import sys
import os
from app_yaml_config import AppYamlConfig
from yaml_config_factory import YamlConfigFactory

# Mock init
# Assuming we are in fastapi_server/
project_root = os.path.dirname(os.getcwd()) # /Users/Shared/autoload/mta-v700
config_dir = os.path.join(project_root, "common", "config")
app_env = "dev"

print(f"Config dir: {config_dir}")

try:
    AppYamlConfig.initialize(
        files=["base.yml", f"server.{{APP_ENV}}.yaml"],
        config_dir=config_dir,
    )
    print("Initialized AppYamlConfig")
except Exception as e:
    print(f"Failed init: {e}")
    # Don't exit, might be already init if running in some context? No, isolated script.
    import traceback
    traceback.print_exc()
    sys.exit(1)

config = AppYamlConfig.get_instance()
factory = YamlConfigFactory(config)

try:
    print("Computing storages.elasticsearch...")
    res = factory.compute_all("storages.elasticsearch")
    print("Result OK")
except Exception as e:
    print(f"Failed elasticsearch: {e}")
    import traceback
    traceback.print_exc()

try:
    print("Computing storages.postgres...")
    res = factory.compute_all("storages.postgres")
    print("Result OK")
except Exception as e:
    print(f"Failed postgres: {e}")
    import traceback
    traceback.print_exc()
