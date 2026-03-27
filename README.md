# SAP BTP Integration Suite Trial - Automated Setup

[Português](#português) | [English](#english)

---

## Português

### Descrição

Script Python reutilizável para automatizar a configuração completa do **SAP Integration Suite** numa conta **SAP BTP Trial**. O script executa automaticamente todos os passos necessários:

1. **Login** na conta SAP BTP via BTP CLI
2. **Criação de subaccount** com região e nome configuráveis
3. **Ativação do Cloud Foundry** (environment, org e space)
4. **Atribuição de entitlements** do Integration Suite
5. **Subscrição do Integration Suite**
6. **Atribuição de role collections** ao utilizador

### Pré-requisitos

- **Python 3.8+**
- **SAP BTP CLI** (`btp`) - [Download](https://tools.hana.ondemand.com/#cloud-btpcli)
- **Cloud Foundry CLI** (`cf`) - [Download](https://github.com/cloudfoundry/cli/releases)
- **PyYAML** - `pip install pyyaml`
- **Conta SAP BTP Trial** ativa - [Criar conta](https://account.hanatrial.ondemand.com/)

### Instalação Rápida

```bash
# 1. Clonar ou copiar os ficheiros
git clone <repo-url>
cd sap-btp-is-automator

# 2. Instalar ferramentas CLI e dependências Python
chmod +x install_cli_tools.sh
./install_cli_tools.sh

# 3. Configurar o ficheiro config.yaml
cp config.yaml config.yaml.bak
nano config.yaml   # Editar com as suas credenciais
```

### Configuração

Edite o ficheiro `config.yaml` com os seus dados:

```yaml
# Credenciais SAP BTP
btp_user: "seu-email@exemplo.com"
btp_password: "sua-senha"

# Subdomain da conta global (encontra-se no URL do BTP Cockpit)
global_account_subdomain: "seu-trial-ga"

# Configuração da subaccount
subaccount:
  display_name: "IS-Trial"
  subdomain: "is-trial"
  region: "us10"          # Regiões comuns: us10, ap21, eu10

# Cloud Foundry
cloud_foundry:
  space_name: "dev"

# Utilizadores e Roles
users:
  admin_user: ""          # Deixe vazio para usar o btp_user
  role_collections:
    - "Integration_Provisioner"
    - "PI_Administrator"
    - "PI_Business_Expert"
    - "PI_Integration_Developer"
```

> **Dica de segurança:** Em vez de colocar credenciais no ficheiro YAML, use variáveis de ambiente:
> ```bash
> export SAP_BTP_USER="seu-email@exemplo.com"
> export SAP_BTP_PASSWORD="sua-senha"
> ```

### Utilização

```bash
# Execução básica com ficheiro de configuração
python setup_integration_suite.py --config config.yaml

# Sobrescrever credenciais via linha de comando
python setup_integration_suite.py --config config.yaml \
    --user seu-email@exemplo.com \
    --password sua-senha

# Modo verbose (debug)
python setup_integration_suite.py --config config.yaml --verbose

# Limpar subaccount existente e recriar (quando o trial expira)
python setup_integration_suite.py --config config.yaml --cleanup

# Pular etapas específicas
python setup_integration_suite.py --config config.yaml --skip-cf
python setup_integration_suite.py --config config.yaml --skip-roles
```

### Opções da Linha de Comando

| Opção | Descrição |
|---|---|
| `--config`, `-c` | Caminho para o ficheiro de configuração YAML (padrão: `config.yaml`) |
| `--user`, `-u` | Email do utilizador SAP BTP (sobrescreve config) |
| `--password`, `-p` | Password SAP BTP (sobrescreve config) |
| `--global-account` | Subdomain da conta global (sobrescreve config) |
| `--region` | Região da subaccount (sobrescreve config) |
| `--verbose`, `-v` | Ativar logging detalhado |
| `--cleanup` | Apagar subaccount existente antes de recriar |
| `--skip-cf` | Pular configuração do Cloud Foundry |
| `--skip-subscribe` | Pular subscrição do Integration Suite |
| `--skip-roles` | Pular atribuição de role collections |

### Passos Manuais Após o Script

Após a execução do script, é necessário ativar as capacidades do Integration Suite manualmente (limitação da API):

1. Abrir o [SAP BTP Cockpit](https://cockpit.btp.cloud.sap)
2. Navegar até a subaccount criada
3. Ir a **Instances and Subscriptions**
4. Clicar em **Integration Suite** → **Go to Application**
5. Na página do Integration Suite, clicar em **Add Capabilities**
6. Selecionar:
   - ✅ Build Integration Scenarios (Cloud Integration)
   - ✅ Manage APIs (API Management)
7. Clicar em **Activate**

### Reutilização (Quando o Trial Expira)

Quando a conta trial expirar, basta executar novamente:

```bash
# Opção 1: Recriar tudo do zero
python setup_integration_suite.py --config config.yaml --cleanup

# Opção 2: Tentar reutilizar o que existir
python setup_integration_suite.py --config config.yaml
```

### Como Encontrar o Subdomain da Conta Global

1. Acesse [https://cockpit.btp.cloud.sap](https://cockpit.btp.cloud.sap)
2. Faça login com a sua conta SAP
3. O subdomain aparece no URL após o login, ex: `https://cockpit.btp.cloud.sap/cockpit/#/globalaccount/abc123-trial-ga/`
4. O subdomain é: `abc123-trial-ga`

---

## English

### Description

Reusable Python script to automate the complete setup of **SAP Integration Suite** on a **SAP BTP Trial** account. The script automatically performs all required steps:

1. **Login** to SAP BTP via BTP CLI
2. **Create subaccount** with configurable region and name
3. **Enable Cloud Foundry** (environment, org, and space)
4. **Assign entitlements** for Integration Suite
5. **Subscribe to Integration Suite**
6. **Assign role collections** to users

### Prerequisites

- **Python 3.8+**
- **SAP BTP CLI** (`btp`) - [Download](https://tools.hana.ondemand.com/#cloud-btpcli)
- **Cloud Foundry CLI** (`cf`) - [Download](https://github.com/cloudfoundry/cli/releases)
- **PyYAML** - `pip install pyyaml`
- **Active SAP BTP Trial account** - [Create account](https://account.hanatrial.ondemand.com/)

### Quick Start

```bash
# 1. Clone or copy the files
git clone <repo-url>
cd sap-btp-is-automator

# 2. Install CLI tools and Python dependencies
chmod +x install_cli_tools.sh
./install_cli_tools.sh

# 3. Configure config.yaml
cp config.yaml config.yaml.bak
nano config.yaml   # Edit with your credentials
```

### Configuration

Edit `config.yaml` with your details:

```yaml
# SAP BTP credentials
btp_user: "your-email@example.com"
btp_password: "your-password"

# Global account subdomain (found in the BTP Cockpit URL)
global_account_subdomain: "your-trial-ga"

# Subaccount settings
subaccount:
  display_name: "IS-Trial"
  subdomain: "is-trial"
  region: "us10"          # Common trial regions: us10, ap21, eu10

# Cloud Foundry
cloud_foundry:
  space_name: "dev"

# Users and Roles
users:
  admin_user: ""          # Leave empty to use btp_user
  role_collections:
    - "Integration_Provisioner"
    - "PI_Administrator"
    - "PI_Business_Expert"
    - "PI_Integration_Developer"
```

> **Security tip:** Instead of putting credentials in the YAML file, use environment variables:
> ```bash
> export SAP_BTP_USER="your-email@example.com"
> export SAP_BTP_PASSWORD="your-password"
> ```

### Usage

```bash
# Basic execution with config file
python setup_integration_suite.py --config config.yaml

# Override credentials via command line
python setup_integration_suite.py --config config.yaml \
    --user your-email@example.com \
    --password your-password

# Verbose mode (debug)
python setup_integration_suite.py --config config.yaml --verbose

# Clean up existing subaccount and recreate (when trial expires)
python setup_integration_suite.py --config config.yaml --cleanup

# Skip specific steps
python setup_integration_suite.py --config config.yaml --skip-cf
python setup_integration_suite.py --config config.yaml --skip-roles
```

### Command Line Options

| Option | Description |
|---|---|
| `--config`, `-c` | Path to YAML config file (default: `config.yaml`) |
| `--user`, `-u` | SAP BTP user email (overrides config) |
| `--password`, `-p` | SAP BTP password (overrides config) |
| `--global-account` | Global account subdomain (overrides config) |
| `--region` | Subaccount region (overrides config) |
| `--verbose`, `-v` | Enable detailed logging |
| `--cleanup` | Delete existing subaccount before recreating |
| `--skip-cf` | Skip Cloud Foundry environment setup |
| `--skip-subscribe` | Skip Integration Suite subscription |
| `--skip-roles` | Skip role collection assignment |

### Manual Steps After Script

After running the script, you need to activate Integration Suite capabilities manually (API limitation):

1. Open the [SAP BTP Cockpit](https://cockpit.btp.cloud.sap)
2. Navigate to the created subaccount
3. Go to **Instances and Subscriptions**
4. Click on **Integration Suite** → **Go to Application**
5. In the Integration Suite page, click **Add Capabilities**
6. Select:
   - ✅ Build Integration Scenarios (Cloud Integration)
   - ✅ Manage APIs (API Management)
7. Click **Activate**

### Reuse (When Trial Expires)

When the trial account expires, simply run again:

```bash
# Option 1: Recreate everything from scratch
python setup_integration_suite.py --config config.yaml --cleanup

# Option 2: Try to reuse what exists
python setup_integration_suite.py --config config.yaml
```

### How to Find Your Global Account Subdomain

1. Go to [https://cockpit.btp.cloud.sap](https://cockpit.btp.cloud.sap)
2. Login with your SAP account
3. The subdomain appears in the URL after login, e.g.: `https://cockpit.btp.cloud.sap/cockpit/#/globalaccount/abc123-trial-ga/`
4. The subdomain is: `abc123-trial-ga`

---

## Project Structure

```
sap-btp-is-automator/
├── setup_integration_suite.py   # Main automation script
├── config.yaml                  # Configuration file (edit before use)
├── install_cli_tools.sh         # CLI tools installer
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## License

MIT License - Free to use, modify, and distribute.
