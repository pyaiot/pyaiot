# Example configuration file for for Pyaiot

# Configuration options are shared between all pyaiot components.


# Debug
# Enable debug logging for all components.
#debug = False

# Broker host:
# Other component connect to this host for their broker connection. The
# dashboard passes this hostname to the clients for their broker connection.
#broker_host = 'localhost'

# Broker port number:
# This is the tcp port number the websocket of the broker is listening on. Other
# component use this configuration options to determine which port number to
# connect to.
#broker_port = 8020

# Key file
# The key file is necessary to authenticate different components to the broker.
# Both the broker and the other components use the path specified to find the
# key file for authentication.
#key_file = '~/.pyaiot/keys'

# coap port
# The coap component listens on this port for CoAP messages from nodes
#coap_port = 5683

# MQTT host
# The hostname of the MQTT broker. The mqtt component connects to this hostname
# for the MQTT broker connection.
#mqtt_host = 'localhost'

# MQTT port
# The port the MQTT broker listens on. The MQTT component connects to this port
# on the MQTT broker.
#mqtt_port = 1886

# Gateway port
# This port is used by the websocket gateway to listen on. Websocket nodes
# connect to this port to connect with the websocket gateway.
#gateway_port = 8001

# max time
# Both the CoAP broker and the MQTT broker remove nodes from the broker after
# this many seconds without any messages from a node.
#max_time = 120

# Web Port
# The web interface listens on this port for HTTP connections.
#web_port = 8080

# Broker SSL
# When enabled, the URI to the broker is supplied with wss to indicate to use
# SSL to connect to the broker. Use this when you have a reverse proxy in front
# of the dashboard to handle SSL termination.
#broker_ssl=False

# Camera URL
# The HTTP clients get this URL for their connection to webcam images. If None
# is configured, no webcam functionality is configured
#camera_url = None

# Title
# The title of the web page.
#title = 'IoT Dashboard'

# Logo
# The logo for the navbar of the dashboard. Should be an URL to the image. If
# None is configured, no logo is shown.
#logo = None

# Favicon
# Optionally show a favicon on the dashboard. Should be an URL to an image. If
# None is configured, no favicon is passed to the web page.
#favicon = None
