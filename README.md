# PARVAL

**PARVAL**: Large Language Models for Validating Network Protocol Parsers  
_Accepted at LangSec '25_

📄 [Read the paper](https://arxiv.org/abs/2504.13515)

---

We public the parser isolation agent framework.

### Step 1: Configure the Tool

Edit the `config_list` variable in `isolate.py` to specify your model and API settings.

### Step 2: Run the following command:

```bash
python isolate.py --fun <FUNCTION_NAME> --file_path <FILE_PATH> --proj_path <PROJECT_PATH>
```

### Arguments

- `--fun <FUNCTION_NAME>`  
  Entry point parsing function to analyze.

- `--file_path <FILE_PATH>`  
  Path to the file containing the parsing function.

- `--proj_path <PROJECT_PATH>`  
  Root directory of the target project.

- `-h`, `--help`  
  Show help message and exit.