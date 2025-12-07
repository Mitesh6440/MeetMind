// Task Management
let allTasks = [];
let teamMembers = [];
let currentView = 'cards'; // 'cards' or 'table'

// Load team members
async function loadTeamMembers() {
    try {
        const team = await API.getTeam();
        teamMembers = team.members;
        
        // Populate assignee filter
        const assigneeFilter = document.getElementById('filterAssignee');
        teamMembers.forEach(member => {
            const option = document.createElement('option');
            option.value = member.name;
            option.textContent = member.name;
            assigneeFilter.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load team:', error);
    }
}

// Display tasks
function displayTasks(tasks) {
    allTasks = tasks;
    applyFilters();
    updateSummary(tasks);
}

// Apply filters
function applyFilters() {
    const priorityFilter = document.getElementById('filterPriority').value;
    const assigneeFilter = document.getElementById('filterAssignee').value;
    const statusFilter = document.getElementById('filterStatus').value;

    let filtered = allTasks.filter(task => {
        // Priority filter
        if (priorityFilter !== 'all' && task.priority !== priorityFilter) {
            return false;
        }

        // Assignee filter
        if (assigneeFilter !== 'all' && task.assigned_to !== assigneeFilter) {
            return false;
        }

        // Status filter
        if (statusFilter === 'assigned' && !task.assigned_to) {
            return false;
        }
        if (statusFilter === 'unassigned' && task.assigned_to) {
            return false;
        }

        return true;
    });

    renderTasks(filtered);
}

// Render tasks
function renderTasks(tasks) {
    if (currentView === 'table') {
        renderTasksTable(tasks);
    } else {
        renderTasksCards(tasks);
    }
}

// Render tasks as cards
function renderTasksCards(tasks) {
    const tasksGrid = document.getElementById('tasksGrid');
    tasksGrid.innerHTML = '';

    if (tasks.length === 0) {
        tasksGrid.innerHTML = '<p style="text-align: center; color: var(--text-secondary); grid-column: 1 / -1;">No tasks found matching the filters.</p>';
        return;
    }

    tasks.forEach(task => {
        const taskCard = createTaskCard(task);
        tasksGrid.appendChild(taskCard);
    });
}

// Render tasks as table
function renderTasksTable(tasks) {
    const tableBody = document.getElementById('tasksTableBody');
    tableBody.innerHTML = '';

    if (tasks.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-secondary); padding: 2rem;">No tasks found matching the filters.</td></tr>';
        return;
    }

    tasks.forEach(task => {
        const row = createTaskTableRow(task);
        tableBody.appendChild(row);
    });
}

// Create table row for a task
function createTaskTableRow(task) {
    const row = document.createElement('tr');
    row.onclick = () => showTaskModal(task);
    row.style.cursor = 'pointer';
    row.className = 'task-table-row';

    // Format deadline
    let deadlineText = 'Not set';
    if (task.deadline) {
        const deadlineDate = new Date(task.deadline);
        deadlineText = deadlineDate.toLocaleDateString() + ' ' + deadlineDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    // Format priority
    const priority = task.priority || 'Not set';
    const priorityClass = task.priority ? `priority-${task.priority}` : '';

    // Format assigned to
    const assignedTo = task.assigned_to || 'Unassigned';
    const assignedClass = task.assigned_to ? '' : 'unassigned';

    // Format dependencies
    let dependenciesText = 'None';
    if (task.dependencies && task.dependencies.length > 0) {
        dependenciesText = task.dependencies.map(dep => `Task ${dep}`).join(', ');
    }

    // Format reason (assignment reasoning)
    const reason = task.assignment_reasoning || 'No reasoning provided';
    const truncatedReason = reason.length > 100 ? reason.substring(0, 100) + '...' : reason;

    row.innerHTML = `
        <td class="task-description-cell">${escapeHtml(task.description)}</td>
        <td class="task-assignee-cell ${assignedClass}">${escapeHtml(assignedTo)}</td>
        <td class="task-deadline-cell">${deadlineText}</td>
        <td class="task-priority-cell">
            ${task.priority ? `<span class="task-priority ${priorityClass}">${priority}</span>` : '<span class="task-priority">Not set</span>'}
        </td>
        <td class="task-dependencies-cell">${escapeHtml(dependenciesText)}</td>
        <td class="task-reason-cell" title="${escapeHtml(reason)}">${escapeHtml(truncatedReason)}</td>
    `;

    return row;
}

// Switch between card and table view
function switchView(view) {
    currentView = view;
    
    const tasksGrid = document.getElementById('tasksGrid');
    const tasksTableContainer = document.getElementById('tasksTableContainer');
    const cardViewBtn = document.getElementById('cardViewBtn');
    const tableViewBtn = document.getElementById('tableViewBtn');

    if (view === 'table') {
        tasksGrid.style.display = 'none';
        tasksTableContainer.style.display = 'block';
        cardViewBtn.classList.remove('active');
        tableViewBtn.classList.add('active');
    } else {
        tasksGrid.style.display = 'grid';
        tasksTableContainer.style.display = 'none';
        cardViewBtn.classList.add('active');
        tableViewBtn.classList.remove('active');
    }

    // Re-render with current filters
    applyFilters();
}

// Create task card
function createTaskCard(task) {
    const card = document.createElement('div');
    card.className = `task-card priority-${task.priority || 'medium'}`;
    card.onclick = () => showTaskModal(task);

    const deadline = task.deadline ? new Date(task.deadline).toLocaleDateString() : null;
    const deadlineTime = task.deadline ? new Date(task.deadline).toLocaleTimeString() : null;

    card.innerHTML = `
        <div class="task-header">
            <span class="task-id">Task #${task.id}</span>
            ${task.priority ? `<span class="task-priority ${task.priority}">${task.priority}</span>` : ''}
        </div>
        <div class="task-description">${escapeHtml(task.description)}</div>
        <div class="task-meta">
            ${task.assigned_to ? `
                <div class="task-meta-item">
                    <strong>Assigned to:</strong> ${escapeHtml(task.assigned_to)}
                </div>
            ` : ''}
            ${deadline ? `
                <div class="task-meta-item">
                    <strong>Deadline:</strong> ${deadline} ${deadlineTime}
                </div>
            ` : ''}
            ${task.assignment_confidence ? `
                <div class="task-meta-item">
                    <strong>Confidence:</strong> ${Math.round(task.assignment_confidence * 100)}%
                </div>
            ` : ''}
        </div>
        ${task.assigned_to ? `
            <div class="task-assignee">
                <span>👤</span>
                <span>${escapeHtml(task.assigned_to)}</span>
            </div>
        ` : `
            <div class="task-assignee unassigned">
                <span>⚠️</span>
                <span>Unassigned</span>
            </div>
        `}
        ${task.required_skills && task.required_skills.length > 0 ? `
            <div class="task-tags">
                ${task.required_skills.map(skill => `<span class="task-tag">${escapeHtml(skill)}</span>`).join('')}
            </div>
        ` : ''}
    `;

    return card;
}

// Update summary
function updateSummary(tasks) {
    document.getElementById('totalTasks').textContent = tasks.length;
    document.getElementById('assignedTasks').textContent = tasks.filter(t => t.assigned_to).length;
    document.getElementById('tasksWithDeadline').textContent = tasks.filter(t => t.deadline).length;
    document.getElementById('criticalTasks').textContent = tasks.filter(t => t.priority === 'critical').length;
}

// Clear filters
function clearFilters() {
    document.getElementById('filterPriority').value = 'all';
    document.getElementById('filterAssignee').value = 'all';
    document.getElementById('filterStatus').value = 'all';
    applyFilters();
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Make switchView globally accessible
window.switchView = switchView;

// Initialize filters
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('filterPriority').addEventListener('change', applyFilters);
    document.getElementById('filterAssignee').addEventListener('change', applyFilters);
    document.getElementById('filterStatus').addEventListener('change', applyFilters);
    loadTeamMembers();
});

