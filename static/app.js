// Initialize socket connection
const socket = io();

// DOM Elements
const setupSection = document.getElementById('setup-section');
const chatSection = document.getElementById('chat-section');
const setupForm = document.getElementById('setup-form');
const queryForm = document.getElementById('query-form');
const queryInput = document.getElementById('query-input');
const loadingContainer = document.getElementById('loading-container');
const responseContainer = document.getElementById('response-container');
const graphContainer = document.getElementById('graph-container');

// Handle setup form submission
setupForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const vaultPath = document.getElementById('vault-select').value;
    const modelName = document.getElementById('model-select').value;
    
    // Show loading state
    setupForm.querySelector('button').disabled = true;
    setupForm.querySelector('button').textContent = 'Initializing...';
    
    // Emit initialize event
    socket.emit('initialize', {
        vault_path: vaultPath,
        model_name: modelName
    });
});

// Handle initialization response
socket.on('initialize_response', (data) => {
    if (data.status === 'success') {
        // Hide setup section and show chat section
        setupSection.style.display = 'none';
        chatSection.style.display = 'block';
    } else {
        alert('Initialization failed: ' + data.message);
    }
    
    // Reset setup form
    setupForm.querySelector('button').disabled = false;
    setupForm.querySelector('button').textContent = 'Initialize';
});

// Handle query form submission
queryForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = queryInput.value.trim();
    
    if (!query) return;

    // Show loading spinner
    loadingContainer.style.display = 'flex';
    responseContainer.innerHTML = '';
    graphContainer.style.display = 'none';

    // Emit query event
    socket.emit('query', { query });

    // Clear input
    queryInput.value = '';
});

// Handle query response
socket.on('query_response', (data) => {
    // Hide loading spinner
    loadingContainer.style.display = 'none';

    if (data.status === 'error') {
        responseContainer.innerHTML = `<div class="error">${data.message}</div>`;
        return;
    }

    // Update response container with markdown content
    responseContainer.innerHTML = data.response;

    // Update graph if files are provided
    if (data.files && data.files.length > 0) {
        graphContainer.style.display = 'block';
        updateGraph(data.files);
    }
});

// Handle connection status
socket.on('connect', () => {
    console.log('Connected to server');
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
});

// Graph visualization functions
function updateGraph(files) {
    // Create nodes for each file
    const nodes = files.map((file, index) => ({
        id: index,
        label: file.name,
        title: file.path
    }));

    // Create edges between files
    const edges = [];
    for (let i = 0; i < files.length - 1; i++) {
        edges.push({
            from: i,
            to: i + 1
        });
    }

    // Create the network
    const data = {
        nodes: new vis.DataSet(nodes),
        edges: new vis.DataSet(edges)
    };

    const options = {
        nodes: {
            shape: 'dot',
            size: 16,
            font: {
                size: 12
            },
            borderWidth: 2,
            shadow: true
        },
        edges: {
            width: 1,
            shadow: true
        },
        physics: {
            stabilization: false
        }
    };

    // Initialize or update the network
    if (!window.network) {
        window.network = new vis.Network(graphContainer, data, options);
    } else {
        window.network.setData(data);
    }
} 