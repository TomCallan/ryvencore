/**
 * Log panel & footer management.
 */
import { state } from './state.js';
import * as API from './api.js';

let lastLogHash = '';

export function togglePanel() {
    const panel = $('#logs-panel');
    const icon = $('#logs-toggle-icon');
    if (panel.hasClass('closed')) {
        panel.removeClass('closed').addClass('open');
        icon.text('keyboard_arrow_down');
    } else {
        panel.removeClass('open').addClass('closed');
        icon.text('keyboard_arrow_up');
    }
}

export function loadLogs() {
    if (state.viewPaused) return;
    API.getLogs().then(logs => {
        if (!logs || logs.length === 0) {
            if (lastLogHash !== '') {
                $('#log-list').empty();
                $('#log-count').text('0');
                lastLogHash = '';
            }
            return;
        }
        const latest = logs[logs.length - 1];
        const hash = `${latest.time}_${latest.msg}_${logs.length}`;
        if (hash === lastLogHash) return;
        lastLogHash = hash;

        const list = $('#log-list').empty();
        logs.forEach(log => {
            const isStudio = log.msg.startsWith('[Studio UI]:');
            list.append($(`
                <div class="log-entry">
                    <span class="log-time">[${log.time}]</span>
                    <span class="log-msg" ${isStudio ? 'style="color:#6366f1"' : ''}>${log.msg}</span>
                </div>
            `));
        });
        $('#log-count').text(logs.length);
        $('.footer-body').scrollTop($('.footer-body')[0].scrollHeight);
    });
}

export function addLog(msg) {
    API.addServerLog(`[Studio UI]: ${msg}`).then(() => loadLogs());
}

/** Start periodic log polling */
export function startLogPolling() {
    setInterval(loadLogs, 2000);
}
