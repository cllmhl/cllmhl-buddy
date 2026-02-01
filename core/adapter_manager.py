from typing import List, Dict, Any
import logging
from adapters.factory import AdapterFactory
from core.commands import AdapterCommand
from core.events import InputEvent, InputEventType

class AdapterManager:

    def __init__(self, config: Dict[str, Any], input_queue):
        self.config = config
        self.input_queue = input_queue
        self.logger = logging.getLogger(__name__)
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
                self.input_queue
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

    def handle_event(self, event: InputEvent):
        """
        Per alcuni eventi dobbiamo inviare comandi specifici agli adapter.
        """
        commands: List[AdapterCommand] = []
        if event.type == InputEventType.WAKEWORD:
            commands.append(AdapterCommand.WAKEWORD_LISTEN_STOP)
            commands.append(AdapterCommand.VOICE_INPUT_START)
        elif event.type == InputEventType.CONVERSATION_END:
            commands.append(AdapterCommand.WAKEWORD_LISTEN_START)
        elif event.type == InputEventType.USER_SPEECH: # barge-in
            commands.append(AdapterCommand.VOICE_OUTPUT_STOP)
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
                self.logger.info(f"⚠️  Command {command.value} not handled by any adapter")
            else:
                self.logger.info(f"🎯 Command {command.value} handled by {handled_count} adapter(s)")
