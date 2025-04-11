#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Find vaults
find_vaults() {
    local home="$HOME"
    local vaults=()
    for dir in "$home/Documents/Obsidian" "$home/Desktop" "$home/Documents" "$home"; do
        if [ -d "$dir" ]; then
            for item in "$dir"/*; do
                if [ -d "$item" ] && [ -d "$item/.obsidian" ]; then
                    vaults+=("$item")
                fi
            done
        fi
    done
    echo "${vaults[@]}"
}

# Get Ollama models
get_models() {
    curl -s http://localhost:11434/api/tags | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print('\n'.join(model['name'] for model in data.get('models', [])))
except:
    print('Error')
"
}

# Run AI assistant
run_ai() {
    local vault="$1"
    local model="$2"
    
    cat > run_ai.py << 'EOF'
import sys
import time
import json
import threading
from pathlib import Path

sys.path.append("SCRIPT_DIR")
from obsidian_ai import ObsidianAI

class CleanOutput:
    def print(self, *args):
        if not args:
            return
        msg = ' '.join(str(arg) for arg in args)
        if msg.startswith("{") and msg.endswith("}"):
            try:
                data = json.loads(msg)
                if "response" in data:
                    text = data["response"]
                    # Clean formatting
                    for char in ['*', '`', '[', ']', '(', ')', '#', '>', '-']:
                        text = text.replace(char, '')
                    # Clean empty lines and extra whitespace
                    lines = []
                    for line in text.split('\n'):
                        line = line.strip()
                        if line and not line.startswith('http'):
                            lines.append(line)
                    # print('\n'.join(lines))
            except:
                pass

def thinking_animation():
    chars = '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    i = 0
    while running:
        print(f"\r{chars[i]} Thinking...", end='', flush=True)
        i = (i + 1) % len(chars)
        time.sleep(0.1)
    # print("\r" + " " * 50 + "\r", end='', flush=True)

def main():
    ai = ObsidianAI("VAULT_PATH", "MODEL_NAME")
    ai.console = CleanOutput()
    
    while True:
        try:
            query = input("\n> ")
            if query.lower() == 'exit':
                break
            
            files = ai.search_notes(query)
            if not files:
                continue
            
            context = ""
            for path, content in files[:3]:
                context += f"\nFile: {path.name}\n{content}\n"
            
            global running
            running = True
            thread = threading.Thread(target=thinking_animation)
            thread.daemon = True
            thread.start()
            
            response = ai.query_ollama(query, context)
            
            running = False
            thread.join(timeout=0.5)
            # print("\r" + " " * 50 + "\r", end='', flush=True)
            
            if response:
                # Clean formatting
                for char in ['*', '`', '[', ']', '(', ')', '#', '>', '-']:
                    response = response.replace(char, '')
                # Clean empty lines and extra whitespace
                lines = []
                for line in response.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('http'):
                        lines.append(line)
                # print('\n'.join(lines))

                print("\n----------------------------------------------------------------")
                print(response)
                print("----------------------------------------------------------------")
                
        except KeyboardInterrupt:
            break
        except:
            continue

if __name__ == "__main__":
    main()
EOF

    # Replace placeholders in the Python script
    sed -i '' "s|SCRIPT_DIR|$SCRIPT_DIR|g" run_ai.py
    sed -i '' "s|VAULT_PATH|$vault|g" run_ai.py
    sed -i '' "s|MODEL_NAME|$model|g" run_ai.py
    
    python3 run_ai.py
    rm run_ai.py
}

# Main script
if [ ! -z "$1" ]; then
    vault="$1"
else
    vaults=($(find_vaults))
    if [ ${#vaults[@]} -eq 0 ]; then
        read -p "> " vault
    else
        for i in "${!vaults[@]}"; do
            echo "$((i+1))) ${vaults[$i]}"
        done
        read -p "> " choice
        if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -le "${#vaults[@]}" ]; then
            vault="${vaults[$((choice-1))]}"
        else
            read -p "> " vault
        fi
    fi
fi

models=($(get_models))
if [ ${#models[@]} -eq 0 ]; then
    echo "No Ollama models found. Start Ollama first."
    exit 1
fi

for i in "${!models[@]}"; do
    echo "$((i+1))) ${models[$i]}"
done

read -p "> " choice
if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -le "${#models[@]}" ]; then
    model="${models[$((choice-1))]}"
else
    read -p "> " model
fi

run_ai "$vault" "$model" 