// Main JavaScript file for asynchronous UI updates
document.addEventListener('DOMContentLoaded', function() {

    // --- Form Handlers ---
    const addJobForm = document.getElementById('add-job-form');
    if (addJobForm) addJobForm.addEventListener('submit', handleFormSubmit);

    const addChannelForm = document.getElementById('add-channel-form');
    if (addChannelForm) addChannelForm.addEventListener('submit', handleFormSubmit);

    const editJobForm = document.getElementById('edit-job-form');
    if (editJobForm) editJobForm.addEventListener('submit', handleFormSubmit);

    const addTeamForm = document.getElementById('add-team-form');
    if (addTeamForm) addTeamForm.addEventListener('submit', handleFormSubmit);

    const addMemberForm = document.getElementById('add-member-form');
    if (addMemberForm) addMemberForm.addEventListener('submit', handleFormSubmit);

    // --- Event Delegation ---
    const jobsTableBody = document.getElementById('jobs-table-body');
    if (jobsTableBody) jobsTableBody.addEventListener('submit', handleDelegatedSubmit);

    const channelList = document.getElementById('channel-list');
    if (channelList) channelList.addEventListener('submit', handleDelegatedSubmit);

    // Delegate for team/member pages (forms live in table bodies)
    document.body.addEventListener('submit', function(event) {
        const form = event.target;
        if (form.matches('.delete-team-form') || form.matches('.delete-member-form')
            || form.matches('.clone-team-form')) {
            handleDelegatedSubmit(event);
        }
    });

    // Rename team (prompt-based)
    document.querySelectorAll('.rename-team-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const currentName = btn.dataset.name;
            const newName = prompt('Rename team:', currentName);
            if (!newName || newName.trim() === currentName) return;
            const formData = new FormData();
            formData.append('name', newName.trim());
            fetch(btn.dataset.url, { method: 'POST', body: formData })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        showAlert(data.message, 'success');
                        setTimeout(() => window.location.reload(), 1000);
                    } else { showAlert(data.message, 'danger'); }
                })
                .catch(() => showAlert('An unexpected error occurred.', 'danger'));
        });
    });

    // --- Delivery Mode Toggle ---
    setupDeliveryMode();

    // --- Message Preview ---
    setupPreviewToggles();

    // --- Frequency Checkboxes ---
    setupFrequencyCheckboxes();

    // --- Search & Sort ---
    setupTableSearch('job-search', 'jobs-table-body');
    setupListSearch('channel-search', 'channel-list');
    setupSortableTable('jobs-table');

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

        if (form.matches('.clone-team-form')) {
            event.preventDefault();
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

        if (form.matches('.delete-team-form') || form.matches('.delete-member-form')) {
            event.preventDefault();
            if (form.matches('.delete-team-form') && !confirm('Are you sure?')) return;
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
        let targetCell;
        if (job.delivery_mode === 'private' && job.team) {
            targetCell = '<i class="bi bi-envelope"></i> ' + escapeHtml(job.team.name);
        } else if (job.channel) {
            targetCell = '<a href="#" title="Room ID: ' + escapeHtml(job.channel.room_id) + '">' + escapeHtml(job.channel.name) + '</a>';
        } else {
            targetCell = '<span class="text-muted">&mdash;</span>';
        }
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
            <td>${targetCell}</td>
            <td>${ownerCell}</td>
            <td>${freq} at ${time} (${tz})</td>
            <td><span class="badge text-bg-${statusClass}">${statusLabel}</span></td>
            <td class="last-run-cell">${lastRun}</td>
            <td class="text-end">
                <div class="btn-group">
                    <form action="${job.urls.run_now}" method="POST" class="d-inline run-now-form"><button type="submit" class="btn btn-sm btn-outline-secondary" title="Run Now"><i class="bi bi-play-fill"></i></button></form>
                    <a href="${job.urls.history}" class="btn btn-sm btn-outline-secondary" title="History"><i class="bi bi-clock-history"></i></a>
                    <a href="${job.urls.edit}" class="btn btn-sm btn-outline-primary" title="Edit"><i class="bi bi-pencil"></i></a>
                    <form action="${job.urls.clone}" method="POST" class="d-inline clone-job-form"><button type="submit" class="btn btn-sm btn-outline-info" title="Clone"><i class="bi bi-files"></i></button></form>
                    <form action="${job.urls.delete}" method="POST" class="d-inline delete-job-form"><button type="submit" class="btn btn-sm btn-outline-danger" title="Delete"><i class="bi bi-trash"></i></button></form>
                </div>
            </td>
        `;
        row.insertAdjacentHTML('afterbegin', html);
    }

    function setupDeliveryMode() {
        const radios = document.querySelectorAll('input[name="delivery_mode"]');
        const channelTarget = document.getElementById('channel-target');
        const teamTarget = document.getElementById('team-target');
        const teamSelect = document.getElementById('team_id');
        const memberPicker = document.getElementById('member-picker');
        if (!radios.length || !channelTarget || !teamTarget) return;

        function toggle() {
            const mode = document.querySelector('input[name="delivery_mode"]:checked').value;
            channelTarget.classList.toggle('d-none', mode !== 'channel');
            teamTarget.classList.toggle('d-none', mode !== 'private');
        }

        radios.forEach(r => r.addEventListener('change', toggle));

        if (teamSelect && memberPicker) {
            teamSelect.addEventListener('change', () => {
                memberPicker.replaceChildren();
                const opt = teamSelect.options[teamSelect.selectedIndex];
                if (!opt || !opt.dataset.members) return;
                try {
                    const teamId = opt.value;
                    fetch('/teams/' + teamId + '/members/list')
                        .then(r => r.json())
                        .then(members => {
                            memberPicker.replaceChildren();
                            members.forEach(m => {
                                const div = document.createElement('div');
                                div.className = 'form-check form-check-inline';
                                const cb = document.createElement('input');
                                cb.className = 'form-check-input';
                                cb.type = 'checkbox';
                                cb.name = 'member_ids';
                                cb.value = m.id;
                                cb.id = 'member-' + m.id;
                                const lbl = document.createElement('label');
                                lbl.className = 'form-check-label';
                                lbl.htmlFor = 'member-' + m.id;
                                lbl.textContent = m.display || m.email;
                                div.appendChild(cb);
                                div.appendChild(lbl);
                                memberPicker.appendChild(div);
                            });
                        })
                        .catch(() => {});
                } catch (e) {}
            });
        }

        toggle();
    }

    function setupPreviewToggles() {
        document.querySelectorAll('.preview-toggle').forEach(btn => {
            btn.addEventListener('click', () => {
                const previewDiv = document.getElementById(btn.dataset.target);
                if (!previewDiv) return;

                const textarea = btn.previousElementSibling || btn.closest('.mb-3').querySelector('textarea');
                if (!textarea) return;

                if (previewDiv.classList.contains('d-none')) {
                    const raw = textarea.value || '';
                    const rendered = renderWebexMarkdown(raw);
                    previewDiv.replaceChildren();
                    const content = document.createElement('div');
                    content.insertAdjacentHTML('afterbegin', rendered);
                    previewDiv.appendChild(content);
                    previewDiv.classList.remove('d-none');
                    btn.querySelector('i').className = 'bi bi-eye-slash';
                } else {
                    previewDiv.classList.add('d-none');
                    btn.querySelector('i').className = 'bi bi-eye';
                }
            });
        });
    }

    function renderWebexMarkdown(text) {
        let processed = text
            .replace(/<@all>/g, '<span class="badge bg-warning text-dark">@all</span>')
            .replace(/<@personEmail:([^|]+)\|?>/g, '<span class="badge bg-primary">@$1</span>');

        if (typeof marked !== 'undefined') {
            return marked.parse(processed);
        }
        return escapeHtml(processed).replace(/\n/g, '<br>');
    }

    function setupFrequencyCheckboxes() {
        const dailyBox = document.getElementById('freq-daily');
        const dayBoxes = document.querySelectorAll('.freq-day');
        const hiddenInput = document.getElementById('frequency');
        if (!dailyBox || !hiddenInput) return;

        function syncHiddenInput() {
            if (dailyBox.checked) {
                hiddenInput.value = 'daily';
                return;
            }
            const checked = Array.from(dayBoxes).filter(cb => cb.checked).map(cb => cb.value);
            hiddenInput.value = checked.length ? checked.join(',') : 'daily';
            if (!checked.length) dailyBox.checked = true;
        }

        dailyBox.addEventListener('change', () => {
            if (dailyBox.checked) {
                dayBoxes.forEach(cb => { cb.checked = false; });
            }
            syncHiddenInput();
        });

        dayBoxes.forEach(cb => {
            cb.addEventListener('change', () => {
                if (cb.checked) dailyBox.checked = false;
                syncHiddenInput();
            });
        });

        syncHiddenInput();
    }

    function setupTableSearch(inputId, tbodyId) {
        const input = document.getElementById(inputId);
        const tbody = document.getElementById(tbodyId);
        if (!input || !tbody) return;
        input.addEventListener('input', () => {
            const q = input.value.trim().toLowerCase();
            for (const row of tbody.rows) {
                if (row.querySelector('td[colspan]')) continue;
                row.style.display = !q || row.textContent.toLowerCase().includes(q) ? '' : 'none';
            }
        });
    }

    function setupListSearch(inputId, listId) {
        const input = document.getElementById(inputId);
        const list = document.getElementById(listId);
        if (!input || !list) return;
        input.addEventListener('input', () => {
            const q = input.value.trim().toLowerCase();
            for (const item of list.children) {
                item.style.display = !q || item.textContent.toLowerCase().includes(q) ? '' : 'none';
            }
        });
    }

    function setupSortableTable(tableId) {
        const table = document.getElementById(tableId);
        if (!table) return;
        const headers = table.querySelectorAll('thead th.sortable');
        headers.forEach((th, idx) => {
            th.addEventListener('click', () => sortTableBy(table, th, idx));
        });
    }

    function sortTableBy(table, th, colIdx) {
        const tbody = table.tBodies[0];
        const rows = Array.from(tbody.rows).filter(r => !r.querySelector('td[colspan]'));
        if (!rows.length) return;

        const isAsc = !th.classList.contains('sort-asc');
        table.querySelectorAll('thead th').forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
        th.classList.add(isAsc ? 'sort-asc' : 'sort-desc');

        rows.sort((a, b) => {
            const av = (a.cells[colIdx]?.textContent || '').trim().toLowerCase();
            const bv = (b.cells[colIdx]?.textContent || '').trim().toLowerCase();
            if (av === bv) return 0;
            return (av < bv ? -1 : 1) * (isAsc ? 1 : -1);
        });
        rows.forEach(r => tbody.appendChild(r));
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
