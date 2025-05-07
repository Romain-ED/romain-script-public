#!/bin/bash
#
# setup_broadchains.sh
#
# Setup script for Broadchains Report Parser
# Created by Romain EDIN for Vonage
#
# This script installs all dependencies required for the Broadchains Report Parser
# Usage: ./setup_broadchains.sh

# Print colored text
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}====================================================================${NC}"
echo -e "${BLUE}          BROADCHAINS REPORT PARSER - SETUP SCRIPT                  ${NC}"
echo -e "${BLUE}====================================================================${NC}"
echo -e "${BLUE}Created by Romain EDIN for Vonage${NC}"
echo

# Check if Python is installed
echo -e "${BLUE}Checking for Python installation...${NC}"
if command -v python3 &>/dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✓ Python is installed: ${PYTHON_VERSION}${NC}"
else
    echo -e "${RED}✗ Python 3 is not installed. Please install Python 3.6 or higher.${NC}"
    echo -e "${YELLOW}Visit https://www.python.org/downloads/ to install Python.${NC}"
    exit 1
fi

# Check if pip is installed
echo -e "${BLUE}Checking for pip installation...${NC}"
if command -v pip3 &>/dev/null || command -v pip &>/dev/null; then
    PIP_CMD=""
    if command -v pip3 &>/dev/null; then
        PIP_CMD="pip3"
    else
        PIP_CMD="pip"
    fi
    echo -e "${GREEN}✓ pip is installed${NC}"
else
    echo -e "${RED}✗ pip is not installed.${NC}"
    echo -e "${YELLOW}Installing pip...${NC}"
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    python3 get-pip.py
    rm get-pip.py
    
    # Check if pip installation was successful
    if command -v pip3 &>/dev/null; then
        PIP_CMD="pip3"
    elif command -v pip &>/dev/null; then
        PIP_CMD="pip"
    else
        echo -e "${RED}Failed to install pip. Please install pip manually.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ pip has been installed${NC}"
fi

# Check if virtual environment module is installed
echo -e "${BLUE}Checking for venv module...${NC}"
if python3 -m venv --help &>/dev/null; then
    echo -e "${GREEN}✓ Python venv module is installed${NC}"
else
    echo -e "${YELLOW}Installing Python venv module...${NC}"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        brew install python3-venv 2>/dev/null || $PIP_CMD install virtualenv
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v apt &>/dev/null; then
            sudo apt update
            sudo apt install -y python3-venv
        elif command -v yum &>/dev/null; then
            sudo yum install -y python3-venv
        else
            $PIP_CMD install virtualenv
        fi
    else
        # Windows or other
        $PIP_CMD install virtualenv
    fi
    echo -e "${GREEN}✓ Python venv module has been installed${NC}"
fi

# Create virtual environment
echo -e "${BLUE}Creating Python virtual environment...${NC}"
if [ -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment already exists. Skipping creation.${NC}"
else
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source venv/bin/activate || . venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Install dependencies
echo -e "${BLUE}Installing required packages...${NC}"
$PIP_CMD install --upgrade pip
$PIP_CMD install pandas numpy colorama

# Check if dependencies were installed successfully
echo -e "${BLUE}Verifying dependencies...${NC}"
MISSING=0

for pkg in pandas numpy colorama; do
    if ! $PIP_CMD show $pkg &>/dev/null; then
        echo -e "${RED}✗ $pkg installation failed${NC}"
        MISSING=1
    else
        PKG_VERSION=$($PIP_CMD show $pkg | grep Version | awk '{print $2}')
        echo -e "${GREEN}✓ $pkg installed (version $PKG_VERSION)${NC}"
    fi
done

if [ $MISSING -eq 1 ]; then
    echo -e "${RED}Some dependencies failed to install. Please try installing them manually:${NC}"
    echo -e "${YELLOW}$PIP_CMD install pandas numpy colorama${NC}"
else
    echo -e "${GREEN}All dependencies installed successfully!${NC}"
fi

# Create activation script
echo -e "${BLUE}Creating activation script...${NC}"
cat > activate_broadchains.sh << 'EOF'
#!/bin/bash
# Activate the Python virtual environment for Broadchains Report Parser
source venv/bin/activate || . venv/bin/activate
echo "Broadchains Report Parser environment activated!"
echo "Run the parser with: python broadchains_report_parser.py input.csv [output_dir]"
EOF

chmod +x activate_broadchains.sh
echo -e "${GREEN}✓ Activation script created: activate_broadchains.sh${NC}"

echo
echo -e "${BLUE}====================================================================${NC}"
echo -e "${GREEN}Setup completed successfully!${NC}"
echo -e "${BLUE}====================================================================${NC}"
echo
echo -e "To use the Broadchains Report Parser:"
echo -e "1. Activate the environment: ${YELLOW}source activate_broadchains.sh${NC}"
echo -e "2. Run the parser: ${YELLOW}python broadchains_report_parser.py input.csv [output_dir]${NC}"
echo

# Make this script executable
chmod +x "$0"
