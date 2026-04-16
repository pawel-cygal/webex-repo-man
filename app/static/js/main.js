// Main JavaScript file for asynchronous UI updates
document.addEventListener('DOMContentLoaded', function() {

    // --- Form Handlers ---
    const addJobForm = document.getElementById('add-job-form');
    if (addJobForm) addJobForm.addEventListener('submit', handleFormSubmit);

    const addChannelForm = document.getElementById('add-channel-form');
    if (addChannelForm) addChannelForm.addEventListener('submit', handleFormSubmit);

    const editJobForm = document.getElementById('edit-job-form');
    if (editJobForm) editJobForm.addEventListener('submit', handleFormSubmit);

    // --- Event Delegation ---
    const jobsTableBody = document.getElementById('jobs-table-body');
    if (jobsTableBody) jobsTableBody.addEventListener('submit', handleDelegatedSubmit);

    const channelList = document.getElementById('channel-list');
    if (channelList) channelList.addEventListener('submit', handleDelegatedSubmit);

    // --- Display session alerts ---
    const alertMessage = sessionStorage.getItem('alertMessage');
    const alertCategory = sessionStorage.getItem('alertCategory');
    if (alertMessage) {
        showAlert(alertMessage, alertCategory);
        sessionStorage.removeItem('alertMessage');
        sessionStorage.removeItem('alertCategory');
    }

    // --- Helpers ---

    function escapeHtml(value) {
        if (value === null || value === undefined) return '';
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    // --- Functions ---

    function handleFormSubmit(event) {
        event.preventDefault();
        const form = event.target;
        const formData = new FormData(form);

        fetch(form.action, {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (data.redirect_url) {
                    sessionStorage.setItem('alertMessage', data.message);
                    sessionStorage.setItem('alertCategory', 'success');
                    window.location.href = data.redirect_url;
                } else if (data.reload) {
                    showAlert(data.message, 'success');
                    setTimeout(() => window.location.reload(), 1000);
                } else if (data.job) {
                    addJobRow(data.job);
                    showAlert(data.message, 'success');
                    form.reset();
                } else {
                    showAlert(data.message, 'success');
                    form.reset();
                }
            } else {
                showAlert(data.message, 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('An unexpected error occurred.', 'danger');
        });
    }

    function handleDelegatedSubmit(event) {
        const form = event.target;

        if (form.matches('.delete-job-form')) {
            event.preventDefault();
            if (confirm('Are you sure you want to delete this job?')) {
                fetch(form.action, { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            form.closest('tr').remove();
                            showAlert(data.message, 'success');
                        } else { showAlert(data.message, 'danger'); }
                    })
                    .catch(err => showAlert('An unexpected error occurred.', 'danger'));
            }
        }

        if (form.matches('.run-now-form')) {
            event.preventDefault();
            fetch(form.action, { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showAlert(data.message, 'success');
                        const lastRunCell = form.closest('tr').querySelector('td.last-run-cell');
                        if (lastRunCell) lastRunCell.textContent = data.job.last_run || '';
                    } else { showAlert(data.message, 'danger'); }
                })
                .catch(err => showAlert('An unexpected error occurred.', 'danger'));
        }

        if (form.matches('.clone-job-form')) {
            event.preventDefault();
            fetch(form.action, { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        addJobRow(data.job);
                        showAlert(data.message, 'success');
                    } else { showAlert(data.message, 'danger'); }
                })
                .catch(err => showAlert('An unexpected error occurred.', 'danger'));
        }

        if (form.matches('.delete-channel-form')) {
            event.preventDefault();
            if (confirm('Are you sure? Deleting a channel will also delete all its jobs.')) {
                fetch(form.action, { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            showAlert(data.message, 'success');
                            if (data.reload) setTimeout(() => window.location.reload(), 1000);
                        } else { showAlert(data.message, 'danger'); }
                    })
                    .catch(err => showAlert('An unexpected error occurred.', 'danger'));
            }
        }
    }

    function addJobRow(job) {
        const tableBody = document.getElementById('jobs-table-body');
        const emptyCell = tableBody.querySelector('td[colspan]');
        if (emptyCell) emptyCell.parentElement.remove();

        const name = escapeHtml(job.name);
        const channelName = escapeHtml(job.channel.name);
        const roomId = escapeHtml(job.channel.room_id);
        const freq = escapeHtml(job.frequency_display);
        const time = escapeHtml(job.schedule_time);
        const tz = escapeHtml(job.timezone);
        const lastRun = job.last_run ? escapeHtml(job.last_run) : '<span class="text-muted">Never</span>';
        const ownerCell = job.owner
            ? escapeHtml(job.owner)
            : '<span class="text-muted fst-italic">Legacy</span>';
        const statusClass = job.is_active ? 'success' : 'secondary';
        const statusLabel = job.is_active ? 'Active' : 'Inactive';

        const row = tableBody.insertRow(0);
        row.id = `job-row-${job.id}`;
        const html = `
            <td>${name}</td>
            <td><a href="#" title="Room ID: ${roomId}">${channelName}</a></td>
            <td>${ownerCell}</td>
            <td>${freq} at ${time} (${tz})</td>
            <td><span class="badge text-bg-${statusClass}">${statusLabel}</span></td>
            <td class="last-run-cell">${lastRun}</td>
            <td class="text-end">
                <div class="btn-group">
                    <form action="${job.urls.run_now}" method="POST" class="d-inline run-now-form"><button type="submit" class="btn btn-sm btn-outline-secondary" title="Run Now"><i class="bi bi-play-fill"></i></button></form>
                    <a href="${job.urls.edit}" class="btn btn-sm btn-outline-primary" title="Edit"><i class="bi bi-pencil"></i></a>
                    <form action="${job.urls.clone}" method="POST" class="d-inline clone-job-form"><button type="submit" class="btn btn-sm btn-outline-info" title="Clone"><i class="bi bi-files"></i></button></form>
                    <form action="${job.urls.delete}" method="POST" class="d-inline delete-job-form"><button type="submit" class="btn btn-sm btn-outline-danger" title="Delete"><i class="bi bi-trash"></i></button></form>
                </div>
            </td>
        `;
        row.insertAdjacentHTML('afterbegin', html);
    }

    function showAlert(message, category = 'primary') {
        const alertContainer = document.querySelector('.container.mt-4');
        const alert = document.createElement('div');
        alert.className = `alert alert-${category} alert-dismissible fade show`;
        alert.role = 'alert';
        const text = document.createElement('span');
        text.textContent = message;
        alert.appendChild(text);
        const closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'btn-close';
        closeBtn.setAttribute('data-bs-dismiss', 'alert');
        closeBtn.setAttribute('aria-label', 'Close');
        alert.appendChild(closeBtn);
        alertContainer.insertBefore(alert, alertContainer.firstChild);
    }
});
