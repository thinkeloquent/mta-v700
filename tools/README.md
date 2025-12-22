# tools-chunking-directory-mapping

```
projscan ./__STAGE__/mta-v600/packages_mjs/app-static-config-yaml --enhanced --format hierarchical
projscan ./__STAGE__/mta-v600/packages_mjs/app-static-config-yaml --enhanced
```

# tools-chunking-directory-mapping (JS)

```
yaml-spec analyze ./__STAGE__/mta-v600/packages_mjs/app-static-config-yaml/src --line-numbers --no-tests -o ./__SPECS__/mta-SPECS/v700/FEATURE/app-static-config-yaml-001.2.py.yaml

node ./tools/source-analyzers/BRD-static-analysis-javascript/dist/index.js generate ./__STAGE__/mta-v600/packages_mjs/app-static-config-yaml/src --output ./__SPECS__/mta-SPECS/v700/FEATURE/app-static-config-yaml-001.5.js.yaml
```

# tools-chunking-directory-mapping (PY)

```
yaml-spec analyze ./__STAGE__/mta-v600/packages_py/app_static_config_yaml/src --line-numbers --no-tests -o ./__SPECS__/mta-SPECS/v700/FEATURE/app-static-config-yaml-001.1.js.yaml

projscan ./__STAGE__/mta-v600/packages_py/app_static_config_yaml --enhanced --format detailed --yaml > ./__SPECS__/mta-SPECS/v700/FEATURE/app-static-config-yaml-001.3.py.yaml

brd-static-analysis-py ./__STAGE__/mta-v600/packages_py/app_static_config_yaml/src --output ./__SPECS__/mta-SPECS/v700/FEATURE/app-static-config-yaml-001.4.py.yaml
```
