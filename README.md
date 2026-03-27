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

- **Python 3.8+** - [Download](https://www.python.org/downloads/)
- **SAP BTP CLI** (`btp`) - [Download](https://tools.hana.ondemand.com/#cloud-btpcli)
- **Cloud Foundry CLI** (`cf`) - [Download](https://github.com/cloudfoundry/cli/releases)
- **PyYAML** - `pip install pyyaml`
- **Conta SAP BTP Trial** ativa - [Criar conta](https://account.hanatrial.ondemand.com/)

---

### Guia Completo de Instalação e Execução (Passo a Passo)

Siga os passos abaixo na ordem indicada para instalar e executar o script com sucesso.

#### Passo 1 — Clonar o repositório

```bash
git clone https://github.com/ricardomourabraga/sap-btp-is-automator.git
cd sap-btp-is-automator
```

#### Passo 2 — Instalar as ferramentas necessárias

O script `install_cli_tools.sh` instala automaticamente o **BTP CLI**, **CF CLI** e a dependência Python **PyYAML**:

```bash
chmod +x install_cli_tools.sh
./install_cli_tools.sh
```

Após a instalação, verifique se tudo foi instalado corretamente:

```bash
btp --version
cf --version
python3 -c "import yaml; print('PyYAML OK')"
```

> **Nota:** Se o script de instalação automática falhar, instale manualmente:
> ```bash
> # BTP CLI (via npm)
> npm install -g @sap/btp-cli
>
> # CF CLI (Linux)
> curl -fsSL "https://packages.cloudfoundry.org/stable?release=linux64-binary&version=v8&source=github" -o /tmp/cf-cli.tgz
> tar -xzf /tmp/cf-cli.tgz -C /tmp && sudo mv /tmp/cf /usr/local/bin/cf
>
> # CF CLI (macOS)
> brew install cloudfoundry/tap/cf-cli@8
>
> # PyYAML
> pip install pyyaml
> ```

#### Passo 3 — Obter o Subdomain da sua Conta Global

Antes de configurar, precisa do subdomain da sua conta global SAP BTP:

1. Acesse [https://cockpit.btp.cloud.sap](https://cockpit.btp.cloud.sap)
2. Faça login com a sua conta SAP
3. Clique em **"Go To Your Trial Account"**
4. O subdomain aparece no URL após o login, por exemplo:
   ```
   https://cockpit.btp.cloud.sap/cockpit/#/globalaccount/abc123def-1234-5678-trial/
   ```
5. O subdomain é: **`abc123def-1234-5678-trial`**

#### Passo 4 — Configurar o ficheiro config.yaml

Faça um backup e edite o ficheiro de configuração:

```bash
cp config.yaml config.yaml.bak
nano config.yaml   # ou use o editor de sua preferência
```

Preencha os campos obrigatórios:

```yaml
# --- CAMPOS OBRIGATÓRIOS ---

# Suas credenciais SAP BTP (email e senha da conta trial)
btp_user: "seu-email@exemplo.com"
btp_password: "sua-senha"

# Subdomain da conta global (obtido no Passo 3)
global_account_subdomain: "abc123def-1234-5678-trial"
```

Os restantes campos já possuem valores padrão adequados para uma conta trial. Pode alterar se necessário:

```yaml
# --- CAMPOS OPCIONAIS (já possuem valores padrão) ---

subaccount:
  display_name: "IS-Trial"     # Nome da subaccount
  subdomain: "is-trial"        # Subdomain da subaccount (deve ser único)
  region: "us10"               # Região (us10, ap21, eu10)

cloud_foundry:
  space_name: "dev"            # Nome do space no Cloud Foundry

users:
  admin_user: ""               # Deixe vazio para usar o btp_user
  role_collections:            # Roles que serão atribuídas
    - "Integration_Provisioner"
    - "PI_Administrator"
    - "PI_Business_Expert"
    - "PI_Integration_Developer"
```

> **Dica de segurança:** Em vez de colocar credenciais no ficheiro YAML, pode usar variáveis de ambiente:
> ```bash
> export SAP_BTP_USER="seu-email@exemplo.com"
> export SAP_BTP_PASSWORD="sua-senha"
> ```
> Nesse caso, deixe os campos `btp_user` e `btp_password` vazios no config.yaml.

#### Passo 5 — Executar o script

```bash
python setup_integration_suite.py --config config.yaml
```

O script vai executar automaticamente as 6 etapas:
```
[STEP 1] Login no SAP BTP
[STEP 2] Criação da subaccount
[STEP 3] Ativação do Cloud Foundry
[STEP 4] Atribuição de entitlements do Integration Suite
[STEP 5] Subscrição do Integration Suite
[STEP 6] Atribuição de role collections
```

> **Tempo estimado:** 5-10 minutos (depende da disponibilidade da SAP).

**Alternativa com credenciais via linha de comando:**
```bash
python setup_integration_suite.py --config config.yaml \
    --user seu-email@exemplo.com \
    --password sua-senha
```

**Alternativa com variáveis de ambiente (mais seguro):**
```bash
export SAP_BTP_USER="seu-email@exemplo.com"
export SAP_BTP_PASSWORD="sua-senha"
python setup_integration_suite.py --config config.yaml
```

**Para ver logs detalhados (modo debug):**
```bash
python setup_integration_suite.py --config config.yaml --verbose
```

#### Passo 6 — Ativar capacidades do Integration Suite (manual)

Após o script terminar com sucesso, é necessário ativar as capacidades manualmente (esta etapa não pode ser automatizada via CLI/API):

1. Abra o [SAP BTP Cockpit](https://cockpit.btp.cloud.sap)
2. Navegue até a subaccount criada (ex: "IS-Trial")
3. No menu lateral, vá a **Services** → **Instances and Subscriptions**
4. Na lista de subscrições, clique em **Integration Suite** → **Go to Application**
5. Na página do Integration Suite, clique em **Add Capabilities**
6. Selecione as capacidades desejadas:
   - **Build Integration Scenarios** (Cloud Integration)
   - **Manage APIs** (API Management)
7. Clique em **Next** → **Next** → **Activate**
8. Aguarde a ativação (pode demorar alguns minutos)

Após a ativação, o Integration Suite está pronto para uso!

---

### Quando o Trial Expirar (Reutilização)

Contas trial da SAP expiram periodicamente. Quando isso acontecer, basta executar novamente:

```bash
# Opção 1: Apagar tudo e recriar do zero
python setup_integration_suite.py --config config.yaml --cleanup

# Opção 2: Tentar reutilizar o que já existir
python setup_integration_suite.py --config config.yaml
```

Depois, repita o **Passo 6** para ativar as capacidades do Integration Suite.

---

### Referência: Opções da Linha de Comando

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

### Resolução de Problemas

| Problema | Solução |
|---|---|
| `btp: command not found` | Execute `./install_cli_tools.sh` ou instale o BTP CLI manualmente |
| `cf: command not found` | Execute `./install_cli_tools.sh` ou instale o CF CLI manualmente |
| `ModuleNotFoundError: No module named 'yaml'` | Execute `pip install pyyaml` |
| Erro de login (credenciais inválidas) | Verifique email/senha e o subdomain da conta global |
| Subaccount já existe | O script detecta automaticamente e reutiliza |
| Trial expirado | Execute com `--cleanup` para recriar tudo |
| Entitlement não disponível | Verifique se a conta trial está ativa no [BTP Cockpit](https://cockpit.btp.cloud.sap) |
| CF environment não fica ready | Pode demorar alguns minutos; o script espera automaticamente |

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

### Quick Start (Step by Step)

```bash
# Step 1 — Clone the repository
git clone https://github.com/ricardomourabraga/sap-btp-is-automator.git
cd sap-btp-is-automator

# Step 2 — Install CLI tools and Python dependencies
chmod +x install_cli_tools.sh
./install_cli_tools.sh

# Step 3 — Configure config.yaml with your SAP credentials
cp config.yaml config.yaml.bak
nano config.yaml

# Step 4 — Run the script
python setup_integration_suite.py --config config.yaml

# Step 5 — (Manual) Activate capabilities in Integration Suite UI
#          See "Manual Steps After Script" below
```

> **Security tip:** Instead of putting credentials in the YAML file, use environment variables:
> ```bash
> export SAP_BTP_USER="your-email@example.com"
> export SAP_BTP_PASSWORD="your-password"
> python setup_integration_suite.py --config config.yaml
> ```

> **When trial expires**, simply run again:
> ```bash
> python setup_integration_suite.py --config config.yaml --cleanup
> ```

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

After running the script, activate Integration Suite capabilities manually (API limitation):

1. Open the [SAP BTP Cockpit](https://cockpit.btp.cloud.sap)
2. Navigate to the created subaccount (e.g., "IS-Trial")
3. Go to **Services** → **Instances and Subscriptions**
4. Click on **Integration Suite** → **Go to Application**
5. In the Integration Suite page, click **Add Capabilities**
6. Select:
   - **Build Integration Scenarios** (Cloud Integration)
   - **Manage APIs** (API Management)
7. Click **Next** → **Next** → **Activate**
8. Wait for activation to complete (may take a few minutes)

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
