import paho.mqtt.client as mqtt
import json

# L'indirizzo della bacheca Mosquitto (essendo sullo stesso Raspberry, è localhost)
BROKER = "localhost"
# Il "canale" esatto su cui scrive la tua porta
TOPIC = "zigbee2mqtt/porta_ingresso" 

# Cosa fare quando ci connettiamo alla bacheca
def on_connect(client, userdata, flags, rc):
    print("✅ Buddy connesso alla rete ZigBee (Broker MQTT)!")
    client.subscribe(TOPIC) # Buddy si "iscrive" al canale della porta

# Cosa fare quando arriva un messaggio dalla porta
def on_message(client, userdata, msg):
    # Trasformiamo il messaggio da testo grezzo a un dizionario Python
    payload = json.loads(msg.payload.decode())
    
    # I sensori Aqara inviano un campo chiamato "contact"
    # True = Magnete vicino (Porta chiusa) | False = Magnete lontano (Porta aperta)
    if "contact" in payload:
        if payload["contact"] == True:
            print("🚪 STATO: La porta è CHIUSA 🟢")
        else:
            print("🚨 STATO: La porta è APERTA 🔴")
            
        # Stampiamo anche la batteria tanto per fare i fighi!
        batteria = payload.get('battery', 'N/A')
        print(f"   [Livello batteria sensore: {batteria}%]")

# --- Avvio del motore ---
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# Ci colleghiamo alla porta standard di Mosquitto (1883)
client.connect(BROKER, 1883, 60)

print("Buddy è in ascolto... Prova ad aprire e chiudere la porta fisica!")
# Questo comando tiene il programma aperto all'infinito ad ascoltare
client.loop_forever()
