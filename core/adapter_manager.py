from typing import List, Dict, Any
import logging
from adapters.factory import AdapterFactory
from core.commands import AdapterCommand
from core.events import InputEvent, InputEventType

class AdapterManager:

    def start_interrupt_handler(self, running_flag_getter):
        """
        Starts the interrupt handler thread. running_flag_getter is a callable returning True if the system is running.
        """
        import threading
        self._interrupt_handler_thread = threading.Thread(
            target=self._interrupt_handler_loop,
            args=(running_flag_getter,),
            daemon=True
        )
        self._interrupt_handler_thread.start()

    def _interrupt_handler_loop(self, running_flag_getter):
        """
        Loop del thread di interruzione. Ascolta sulla interrupt_queue e delega la gestione.
        """
        self.logger.info("🚨 Interrupt handler thread started")
        while running_flag_getter():
            try:
                interrupt_event = self.interrupt_queue.get(timeout=1.0)
                from core.events import InputEventType, create_input_event, EventPriority
                if interrupt_event.type == InputEventType.INTERRUPT:
                    self.logger.warning(f"⚡ INTERRUPT received: {interrupt_event.content}")
                    self.handle_interrupt(interrupt_event)
                    # Inserisci l'evento di interruzione nella coda principale per l'elaborazione
                    event = create_input_event(
                        InputEventType.USER_SPEECH,
                        interrupt_event.content,
                        source="interrupt",
                        priority=EventPriority.HIGH
                    )
                    self.input_queue.put(event)
                self.interrupt_queue.task_done()
            except Exception as e:
                import queue
                if isinstance(e, queue.Empty):
                    continue
                self.logger.error(f"Error in interrupt handler loop: {e}", exc_info=True)
    def __init__(self, config: Dict[str, Any], input_queue, interrupt_queue, logger: logging.Logger):
        self.config = config
        self.input_queue = input_queue
        self.interrupt_queue = interrupt_queue
        self.logger = logger
        self.input_adapters = []
        self.output_adapters = []

    def create_adapters(self):
        # Input Adapters
        for adapter_cfg in self.config['adapters']['input']:
            class_name = adapter_cfg.get('class')
            config = adapter_cfg.get('config', {})
            adapter = AdapterFactory.create_input_adapter(
                class_name,
                config,
                self.input_queue,
                self.interrupt_queue
            )
            if adapter:
                self.input_adapters.append(adapter)
        # Output Adapters
        for adapter_cfg in self.config['adapters']['output']:
            class_name = adapter_cfg.get('class')
            config = adapter_cfg.get('config', {})
            output_adapter = AdapterFactory.create_output_adapter(class_name, config)
            if output_adapter:
                self.output_adapters.append(output_adapter)
        self.logger.info(
            f"✅ Adapters created: {len(self.input_adapters)} input, "
            f"{len(self.output_adapters)} output"
        )

    def start_adapters(self):
        for in_adapter in self.input_adapters:
            try:
                in_adapter.start()
                self.logger.info(f"▶️  Started input adapter: {in_adapter.name}")
            except Exception as e:
                self.logger.error(f"❌ Failed to start {in_adapter.name}: {e}")
        for out_adapter in self.output_adapters:
            try:
                out_adapter.start()
                self.logger.info(f"▶️  Started output adapter: {out_adapter.name}")
            except Exception as e:
                self.logger.error(f"❌ Failed to start {out_adapter.name}: {e}")

    def stop_adapters(self):
        self.logger.info("Stopping adapters...")
        for in_adapter in self.input_adapters:
            try:
                in_adapter.stop()
            except Exception as e:
                self.logger.error(f"Error stopping {in_adapter.name}: {e}")
        for out_adapter in self.output_adapters:
            try:
                out_adapter.stop()
            except Exception as e:
                self.logger.error(f"Error stopping {out_adapter.name}: {e}")

    def handle_interrupt(self, interrupt_event):
        """
        Handles interrupt event: stops voice output on all output adapters.
        """
        handled = 0
        for adapter in self.output_adapters:
            if "VoiceOutput" in adapter.name:
                try:
                    if adapter.handle_command(AdapterCommand.VOICE_OUTPUT_STOP):
                        handled += 1
                        self.logger.debug(f"✅ {adapter.name} handled VOICE_OUTPUT_STOP")
                except Exception as e:
                    self.logger.error(f"❌ Error executing VOICE_OUTPUT_STOP on {adapter.name}: {e}", exc_info=True)
        if handled == 0:
            self.logger.warning("⚠️  VOICE_OUTPUT_STOP not handled by any adapter")
        else:
            self.logger.info(f"🎯 VOICE_OUTPUT_STOP handled by {handled} adapter(s)")

    def handle_event(self, event: InputEvent):
        """
        Handles system commands based on input event, dispatches to adapters.
        Combines logic from _get_system_commands and _execute_commands.
        """
        commands: List[AdapterCommand] = []
        if event.type == InputEventType.WAKEWORD:
            commands.append(AdapterCommand.WAKEWORD_LISTEN_STOP)
            commands.append(AdapterCommand.VOICE_INPUT_START)
        elif event.type == InputEventType.CONVERSATION_END:
            commands.append(AdapterCommand.WAKEWORD_LISTEN_START)
        if not commands:
            return
        for command in commands:
            handled_count = 0
            for adapter in self.input_adapters:
                try:
                    if adapter.handle_command(command):
                        handled_count += 1
                        self.logger.debug(f"✅ {adapter.name} handled {command.value}")
                except Exception as e:
                    self.logger.error(
                        f"❌ Error executing {command.value} on {adapter.name}: {e}",
                        exc_info=True
                    )
            for adapter in self.output_adapters:
                try:
                    if adapter.handle_command(command):
                        handled_count += 1
                        self.logger.debug(f"✅ {adapter.name} handled {command.value}")
                except Exception as e:
                    self.logger.error(
                        f"❌ Error executing {command.value} on {adapter.name}: {e}",
                        exc_info=True
                    )
            if handled_count == 0:
                self.logger.warning(f"⚠️  Command {command.value} not handled by any adapter")
            else:
                self.logger.info(f"🎯 Command {command.value} handled by {handled_count} adapter(s)")
