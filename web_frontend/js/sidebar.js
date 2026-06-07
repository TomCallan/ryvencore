/**
 * Sidebar — Node library, search, drag-to-canvas.
 */
import { state } from './state.js';
import { getNodeCategory } from './nodes.js';
import * as API from './api.js';
import { loadFlow } from './events.js';

export function loadLibrary() {
    API.loadNodeTemplates().then(data => {
        state.nodeTemplates = {};
        const categories = {};

        data.forEach(tpl => {
            state.nodeTemplates[tpl.identifier] = tpl;
            const cat = getNodeCategory(tpl.title);
            if (!categories[cat]) categories[cat] = [];
            categories[cat].push(tpl);
        });

        let html = '';
        Object.keys(categories).sort().forEach(cat => {
            html += `<div class="node-category" data-category="${cat}"><div class="category-title">${cat} Nodes</div>`;
            categories[cat].forEach(tpl => {
                const tagsHtml = (tpl.tags || []).map(t => `<span class="node-tag" data-tag="${t}">${t}</span>`).join('');
                html += `
                    <div class="node-item" draggable="true" data-identifier="${tpl.identifier}" data-category="${cat}">
                        <div class="node-item-main">
                            <span>${tpl.title}</span>
                            <span class="material-icons-round add-icon" title="Add to canvas">add</span>
                        </div>
                        <div class="node-item-tags">${tagsHtml}</div>
                    </div>
                `;
            });
            html += `</div>`;
        });

        $('#node-library').html(html);
        bindSidebarEvents();
    });
}

function bindSidebarEvents() {
    // Click to place at center of viewport
    $('.node-item').off('click').on('click', function () {
        const id = $(this).attr('data-identifier');
        const vp = $('#canvas-viewport');
        const x = (vp.width() / 2 - state.panX) / state.zoom;
        const y = (vp.height() / 2 - state.panY) / state.zoom;
        API.createNode(id, x, y).then(loadFlow);
    });

    // Drag start
    $('.node-item').off('dragstart').on('dragstart', function (e) {
        e.originalEvent.dataTransfer.setData('text/plain', $(this).attr('data-identifier'));
        e.originalEvent.dataTransfer.effectAllowed = 'copy';
    });

    // Search
    $('#node-search').off('input').on('input', function () {
        const q = $(this).val().toLowerCase().trim();
        $('.node-item').each(function () {
            const title = $(this).find('.node-item-main span').first().text().toLowerCase();
            let match = !q || title.includes(q);
            if (!match) {
                $(this).find('.node-tag').each(function () {
                    if ($(this).text().toLowerCase().includes(q)) match = true;
                });
            }
            $(this).toggle(!!match);
        });
        $('.node-category').each(function () {
            $(this).toggle(!!$(this).find('.node-item:visible').length);
        });
    });

    // Click tag to search
    $(document).off('click.tagsearch').on('click.tagsearch', '.node-tag', function (e) {
        e.stopPropagation();
        $('#node-search').val($(this).attr('data-tag')).trigger('input');
    });
}
