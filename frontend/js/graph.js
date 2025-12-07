// Dependency Graph Visualization
let graphChart = null;

// Display dependency graph
function displayDependencyGraph(graphData) {
    const graphSection = document.getElementById('graphSection');
    const canvas = document.getElementById('dependencyGraph');
    
    graphSection.style.display = 'block';

    if (!graphData.edges || graphData.edges.length === 0) {
        canvas.parentElement.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">No dependencies found.</p>';
        return;
    }

    // Prepare data for visualization
    const nodes = new Set();
    const edges = graphData.edges;

    edges.forEach(edge => {
        nodes.add(edge.from_task_id);
        nodes.add(edge.to_task_id);
    });

    const nodeList = Array.from(nodes).map(id => ({ id, label: `Task ${id}` }));

    // Create adjacency list for better visualization
    const adjacencyList = {};
    nodeList.forEach(node => {
        adjacencyList[node.id] = [];
    });

    edges.forEach(edge => {
        if (!adjacencyList[edge.from_task_id]) {
            adjacencyList[edge.from_task_id] = [];
        }
        adjacencyList[edge.from_task_id].push(edge.to_task_id);
    });

    // Create a simple bar chart showing task dependencies
    const ctx = canvas.getContext('2d');
    
    // Destroy existing chart if any
    if (graphChart) {
        graphChart.destroy();
    }

    // Count dependencies per task
    const dependencyCounts = {};
    nodeList.forEach(node => {
        dependencyCounts[node.id] = adjacencyList[node.id].length;
    });

    // Create chart data
    const labels = nodeList.map(n => `Task ${n.id}`);
    const data = nodeList.map(n => dependencyCounts[n.id]);

    graphChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Number of Dependencies',
                data: data,
                backgroundColor: 'rgba(99, 102, 241, 0.6)',
                borderColor: 'rgba(99, 102, 241, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        afterLabel: function(context) {
                            const taskId = parseInt(context.label.replace('Task ', ''));
                            const deps = adjacencyList[taskId] || [];
                            if (deps.length > 0) {
                                return 'Depends on: ' + deps.map(d => `Task ${d}`).join(', ');
                            }
                            return 'No dependencies';
                        }
                    }
                }
            }
        }
    });

    // Add dependency list below chart
    const dependencyList = document.createElement('div');
    dependencyList.className = 'dependency-list';
    dependencyList.style.marginTop = '1.5rem';
    dependencyList.style.padding = '1rem';
    dependencyList.style.backgroundColor = '#f9fafb';
    dependencyList.style.borderRadius = '8px';

    if (graphData.has_cycles) {
        dependencyList.innerHTML = `
            <p style="color: var(--danger-color); font-weight: 600; margin-bottom: 0.5rem;">
                ⚠️ Warning: Circular dependencies detected!
            </p>
        `;
    }

    if (graphData.execution_order && graphData.execution_order.length > 0) {
        dependencyList.innerHTML += `
            <p style="font-weight: 600; margin-bottom: 0.5rem;">Recommended Execution Order:</p>
            <p style="color: var(--text-secondary);">
                ${graphData.execution_order.map(id => `Task ${id}`).join(' → ')}
            </p>
        `;
    }

    dependencyList.innerHTML += `
        <p style="font-weight: 600; margin-top: 1rem; margin-bottom: 0.5rem;">Dependency Relationships:</p>
        <div style="display: grid; gap: 0.5rem;">
            ${edges.map(edge => `
                <div style="padding: 0.5rem; background: white; border-radius: 4px;">
                    Task ${edge.from_task_id} → Task ${edge.to_task_id}
                </div>
            `).join('')}
        </div>
    `;

    canvas.parentElement.appendChild(dependencyList);
}

