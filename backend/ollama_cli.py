import logging
import openlit
import ollama
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

# Enable debug logging for OpenLit and OpenTelemetry to see traces in console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set DEBUG level for opentelemetry.*, openlit.*, and httpx.* loggers
import re

pattern = re.compile(r"^(opentelemetry|openlit|httpx)")
for logger_name in list(logging.root.manager.loggerDict.keys()):
    if pattern.match(logger_name):
        logging.getLogger(logger_name).setLevel(logging.DEBUG)


# Initialize OpenLIT
# Note: Disabling langchain instrumentor due to compatibility issues
# with langchain module structure changes in newer versions
openlit.init(
    otlp_endpoint="http://127.0.0.1:4318",
    application_name="ollama-cli",
    disabled_instrumentors=["langchain"]
)

# Your application code
response = ollama.chat(model='gemma3', messages=[
    {
        'role': 'user',
        'content': 'Why is the sky blue?',
    },
])

#print(response.message.content)