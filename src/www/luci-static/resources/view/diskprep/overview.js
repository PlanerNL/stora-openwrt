'use strict';
'require view';
'require rpc';
'require ui';
'require dom';
'require poll';

var callList = rpc.declare({ object: 'luci.diskprep', method: 'list' });
var callStatus = rpc.declare({ object: 'luci.diskprep', method: 'status' });
var callCreate = rpc.declare({ object: 'luci.diskprep', method: 'create', params: [ 'mode', 'disks', 'label', 'share', 'sharename' ] });
var callRemove = rpc.declare({ object: 'luci.diskprep', method: 'remove', params: [ 'device' ] });
var callAddUser = rpc.declare({ object: 'luci.diskprep', method: 'adduser', params: [ 'user', 'password' ] });
var callDelUser = rpc.declare({ object: 'luci.diskprep', method: 'deluser', params: [ 'user' ] });
var callSmart = rpc.declare({ object: 'luci.diskprep', method: 'smart', params: [ 'disk', 'wake' ] });

/* SMART attributes that point to a dying disk (raw value > 0 is bad) */
var SMART_CRITICAL = { 197: 'pending sector(s)', 198: 'unreadable sector(s)' };
var SMART_WARN = { 5: 'reallocated sector(s)', 187: 'read error(s)' };
var SMART_HIGHLIGHT = { 5: 1, 9: 1, 187: 1, 188: 1, 194: 1, 197: 1, 198: 1, 199: 1 };

var MODES = {
	single: {
		title: 'Single disk',
		descr: 'A regular disk. All of its space is usable.',
		min: 1, max: 1
	},
	raid1: {
		title: 'RAID 1 – mirror (safe)',
		descr: 'Both disks hold exactly the same data. If one fails, your files are still there. Usable space = the smallest disk.',
		min: 2, max: 8
	},
	raid0: {
		title: 'RAID 0 – stripe (large, but fragile)',
		descr: 'The space of the disks is added up and it is a bit faster. Warning: if one disk fails, you lose all files.',
		min: 2, max: 8
	}
};

/* always render as text, never as HTML (labels and names come from disks/users) */
function T(s) {
	return document.createTextNode(s == null ? '' : String(s));
}

function fmtSize(sectors) {
	var b = (+sectors || 0) * 512, u = [ 'B', 'kB', 'MB', 'GB', 'TB' ], i = 0;
	while (b >= 1000 && i < u.length - 1) { b /= 1000; i++; }
	var s = (i >= 3) ? b.toFixed(b < 10 ? 2 : (b < 100 ? 1 : 0)) : String(Math.round(b));
	return s + ' ' + u[i];
}

function isSystemMount(m) {
	return m == '/' || m == '/overlay' || m == '/rom';
}

function diskBusy(d) {
	if (d.md)
		return 'part of RAID volume ' + d.md;
	for (var i = 0; i < d.parts.length; i++) {
		if (d.parts[i].md)
			return 'part of RAID volume ' + d.parts[i].md;
		if (isSystemMount(d.parts[i].mount))
			return 'contains the system';
	}
	if (isSystemMount(d.mount))
		return 'contains the system';
	return null;
}

function diskUsage(d) {
	var out = [];
	if (d.type)
		out.push(d.type + (d.mount ? ', mounted on ' + d.mount : ''));
	d.parts.forEach(function(p) {
		var s = p.name + ': ';
		if (p.md)
			s += 'member of RAID ' + p.md;
		else if (p.type)
			s += p.type + (p.label ? ' "' + p.label + '"' : '');
		else
			s += 'empty / unknown';
		s += ' (' + fmtSize(p.sectors) + ')';
		if (p.mount)
			s += ', mounted on ' + p.mount;
		out.push(s);
	});
	return out.length ? out.join('; ') : 'Empty (not partitioned yet)';
}

function arrayStatus(a) {
	var m = (a.completed || '').match(/^(\d+)\s*\/\s*(\d+)/);
	var pct = m ? (100 * m[1] / m[2]).toFixed(1) + '%' : '';
	if (+a.degraded > 0)
		return E('span', { style: 'color:#c00;font-weight:bold' }, 'Problem: a disk is missing!');
	if (a.action == 'resync' || a.action == 'recover')
		return E('span', { style: 'color:#b70' }, 'Syncing… ' + pct + ' (usable)');
	if (a.action == 'check' || a.action == 'repair')
		return E('span', {}, 'Checking… ' + pct);
	if (a.state == 'inactive')
		return E('span', { style: 'color:#c00' }, 'Inactive');
	return E('span', { style: 'color:#080' }, 'Healthy');
}

function smartRaw(attr) {
	if (!attr || !attr.raw)
		return 0;
	return +attr.raw.value || 0;
}

/* turn smartctl JSON into { state, text, j } */
function smartSummary(res) {
	if (!res)
		return { state: 'loading', text: 'Checking…' };
	if (res.error)
		return { state: 'na', text: res.error };

	var j;
	try { j = JSON.parse(res.json || ''); } catch (e) { j = null; }
	if (!j) {
		var raw = String(res.json || '').replace(/\s+/g, ' ').trim();
		return { state: 'na', text: 'No SMART data (smartctl exit ' + res.rc + (raw ? ': ' + raw.substr(0, 120) : ', no output') + ')' };
	}

	var msgs = ((j.smartctl && j.smartctl.messages) || []).map(function(m) { return m.string; }).join(' ');
	if (!j.smart_status) {
		if (/STANDBY|SLEEP/i.test(msgs))
			return { state: 'sleep', text: 'Asleep (not woken up)', j: j };
		return { state: 'na', text: msgs || 'No SMART data', j: j };
	}

	var attrs = {};
	((j.ata_smart_attributes && j.ata_smart_attributes.table) || []).forEach(function(a) { attrs[a.id] = a; });

	var crit = [], warn = [];
	Object.keys(SMART_CRITICAL).forEach(function(id) {
		var n = smartRaw(attrs[id]);
		if (n > 0) crit.push(n + ' ' + SMART_CRITICAL[id]);
	});
	Object.keys(SMART_WARN).forEach(function(id) {
		var n = smartRaw(attrs[id]);
		if (n > 0) warn.push(n + ' ' + SMART_WARN[id]);
	});

	var extra = [];
	if (j.temperature && j.temperature.current != null)
		extra.push(j.temperature.current + ' °C');
	if (j.power_on_time && j.power_on_time.hours != null)
		extra.push(j.power_on_time.hours + ' h (' + (j.power_on_time.hours / 8766).toFixed(1) + ' years)');
	var suffix = extra.length ? ' · ' + extra.join(' · ') : '';

	if (!j.smart_status.passed)
		return { state: 'bad', text: 'FAILING – replace this disk' + suffix, j: j };
	if (crit.length)
		return { state: 'bad', text: 'Failing sectors: ' + crit.concat(warn).join(', ') + ' – back up and replace' + suffix, j: j };
	if (warn.length)
		return { state: 'warn', text: 'Warning: ' + warn.join(', ') + suffix, j: j };
	return { state: 'good', text: 'Good' + suffix, j: j };
}

var SMART_COLORS = { good: '#080', warn: '#b70', bad: '#c00', sleep: '#666', na: '#666', loading: '#666' };

function table(headers, rows, empty) {
	var t = E('table', { 'class': 'table' }, headers ? [
		E('tr', { 'class': 'tr table-titles' }, headers.map(function(h) {
			return E('th', { 'class': 'th' }, h);
		}))
	] : []);
	if (!rows.length)
		t.appendChild(E('tr', { 'class': 'tr placeholder' }, [
			E('td', { 'class': 'td', 'colspan': headers ? headers.length : 1 }, E('em', {}, empty))
		]));
	rows.forEach(function(r) {
		t.appendChild(E('tr', { 'class': 'tr' }, r.map(function(c) {
			return E('td', { 'class': 'td' }, (typeof c == 'string') ? T(c) : c);
		})));
	});
	return t;
}

function section(title, descr, content) {
	return E('div', { 'class': 'cbi-section' }, [
		E('h3', {}, title),
		descr ? E('div', { 'class': 'cbi-section-descr' }, descr) : '',
		E('div', {}, content)
	]);
}

function notifyError(msg) {
	ui.addNotification(null, E('p', {}, T(msg)), 'danger');
}

return view.extend({
	load: function() {
		return Promise.all([ callList(), callStatus() ]);
	},

	/* ---------- progress dialog for long-running tasks ---------- */
	showProgress: function(title) {
		var pre = E('pre', { 'style': 'max-height:50vh;overflow:auto;white-space:pre-wrap;font-size:85%;background:#111;color:#ddd;padding:.6em;border-radius:4px' }, 'Working…');
		var msg = E('p', {}, E('em', { 'class': 'spinning' }, 'Working, please wait… You can leave this window open.'));
		var btn = E('button', {
			'class': 'btn cbi-button cbi-button-action',
			'disabled': true,
			'click': function() { ui.hideModal(); window.location.reload(); }
		}, 'Close');

		ui.showModal(title, [ msg, pre, E('div', { 'class': 'right' }, btn) ]);

		var tick = function() {
			return callStatus().then(function(st) {
				var atBottom = pre.scrollTop + pre.clientHeight >= pre.scrollHeight - 20;
				pre.textContent = st.log || '';
				if (atBottom)
					pre.scrollTop = pre.scrollHeight;

				if (st.state == 'running') {
					window.setTimeout(tick, 2000);
					return;
				}
				btn.disabled = false;
				if (st.state == 'ok')
					dom.content(msg, E('strong', { 'style': 'color:#080' }, '✔ Done!'));
				else
					dom.content(msg, E('strong', { 'style': 'color:#c00' }, '✘ Something went wrong. See the message at the end of the log.'));
			}).catch(function() {
				window.setTimeout(tick, 3000);
			});
		};
		tick();
	},

	/* ---------- create volume ---------- */
	handleCreate: function(state) {
		var self = this;
		var mode = state.mode();
		var disks = state.disks();
		var label = state.label.value.trim();
		var share = state.share.checked;
		var sharename = state.sharename.value.trim();
		var cfg = MODES[mode];

		if (disks.length < cfg.min || disks.length > cfg.max)
			return notifyError(mode == 'single' ? 'Select exactly one disk.' : 'Select at least two disks for RAID.');
		if (!/^[A-Za-z0-9_-]{1,16}$/.test(label))
			return notifyError('The volume name may only contain letters, digits, - and _ (max. 16 characters).');
		if (share && !/^[A-Za-z0-9_-]{1,32}$/.test(sharename))
			return notifyError('The share name may only contain letters, digits, - and _ (max. 32 characters).');

		var confirm = E('input', { 'type': 'text', 'class': 'cbi-input-text', 'placeholder': 'ERASE', 'autocomplete': 'off' });
		var go = E('button', {
			'class': 'btn cbi-button cbi-button-negative',
			'disabled': true,
			'click': function() {
				ui.hideModal();
				callCreate(mode, disks.map(function(d) { return d.name; }).join(' '), label, share ? '1' : '0', sharename).then(function(res) {
					if (res && res.error)
						return notifyError(res.error);
					self.showProgress('Creating volume "' + label + '"');
				}).catch(function(e) { notifyError('Error: ' + e.message); });
			}
		}, 'Erase and create');
		confirm.addEventListener('input', function() {
			go.disabled = (confirm.value.trim().toUpperCase() != 'ERASE');
		});

		ui.showModal('Are you sure?', [
			E('p', {}, [ E('strong', { 'style': 'color:#c00' }, 'All data on the following disk(s) will be permanently erased:') ]),
			E('ul', {}, disks.map(function(d) {
				return E('li', {}, T(d.name + ' – ' + (d.model || 'unknown model') + ' – ' + fmtSize(d.sectors)));
			})),
			E('p', {}, T('This will create: ' + cfg.title + ', name "' + label + '"' + (share ? ', network share "' + sharename + '".' : '.'))),
			E('p', {}, 'Type ERASE to confirm:'),
			E('p', {}, confirm),
			E('div', { 'class': 'right' }, [
				E('button', { 'class': 'btn cbi-button', 'click': ui.hideModal }, 'Cancel'), ' ',
				go
			])
		]);
		confirm.focus();
	},

	/* ---------- remove RAID ---------- */
	handleRemove: function(a) {
		var self = this;
		var confirm = E('input', { 'type': 'text', 'class': 'cbi-input-text', 'placeholder': 'ERASE', 'autocomplete': 'off' });
		var go = E('button', {
			'class': 'btn cbi-button cbi-button-negative',
			'disabled': true,
			'click': function() {
				ui.hideModal();
				callRemove(a.name).then(function(res) {
					if (res && res.error)
						return notifyError(res.error);
					self.showProgress('Removing RAID volume ' + a.name);
				}).catch(function(e) { notifyError('Error: ' + e.message); });
			}
		}, 'Remove');
		confirm.addEventListener('input', function() {
			go.disabled = (confirm.value.trim().toUpperCase() != 'ERASE');
		});
		ui.showModal('Remove RAID volume ' + a.name + '?', [
			E('p', {}, E('strong', { 'style': 'color:#c00' }, 'All files on this volume will be lost.')),
			E('p', {}, T('The disks (' + a.members.join(', ') + ') can be reused afterwards. A network share on this volume is removed as well.')),
			E('p', {}, 'Type ERASE to confirm:'),
			E('p', {}, confirm),
			E('div', { 'class': 'right' }, [
				E('button', { 'class': 'btn cbi-button', 'click': ui.hideModal }, 'Cancel'), ' ',
				go
			])
		]);
		confirm.focus();
	},

	/* ---------- users ---------- */
	handleAddUser: function(user, pw1, pw2) {
		var u = user.value.trim();
		if (!/^[A-Za-z0-9._-]{1,32}$/.test(u))
			return notifyError('The user name may only contain letters, digits, dot, - and _.');
		if (!pw1.value)
			return notifyError('Please enter a password.');
		if (pw1.value != pw2.value)
			return notifyError('The passwords do not match.');
		return callAddUser(u, pw1.value).then(function(res) {
			if (res && res.error)
				return notifyError(res.error);
			ui.addNotification(null, E('p', {}, T('User "' + u + '" has been saved.')), 'info');
			window.setTimeout(function() { window.location.reload(); }, 800);
		}).catch(function(e) { notifyError('Error: ' + e.message); });
	},

	handleDelUser: function(u) {
		if (!window.confirm('Remove user "' + u + '"?'))
			return;
		return callDelUser(u).then(function(res) {
			if (res && res.error)
				return notifyError(res.error);
			window.location.reload();
		}).catch(function(e) { notifyError('Error: ' + e.message); });
	},

	/* ---------- tables ---------- */
	renderDisks: function(list) {
		var self = this;
		var cols = [ 'Disk', 'Model', 'Size', 'Current use' ];
		if (list.have_smart)
			cols.push('Health (SMART)');
		return table(cols,
			list.disks.map(function(d) {
				var row = [
					E('strong', {}, T(d.name)),
					(d.model || '–') + (d.usb ? ' (USB)' : ''),
					fmtSize(d.sectors),
					diskUsage(d)
				];
				if (list.have_smart)
					row.push(self.renderHealth(d));
				return row;
			}), 'No disks found. Is the disk seated properly?');
	},

	/* ---------- SMART ---------- */
	smartCache: {},

	renderHealth: function(d) {
		var self = this;
		var sum = smartSummary(this.smartCache[d.name]);
		return E('span', {}, [
			E('span', { 'style': 'color:' + SMART_COLORS[sum.state] + ';' + ((sum.state == 'bad') ? 'font-weight:bold' : '') }, T(sum.text)),
			(sum.state != 'loading') ? E('span', {}, [ ' ',
				E('button', {
					'class': 'btn cbi-button cbi-button-action',
					'style': 'padding:0 .5em;line-height:1.6',
					'click': function() { self.showSmart(d, false); }
				}, 'Details')
			]) : ''
		]);
	},

	loadSmart: function(disks, wake) {
		var self = this;
		/* one disk at a time: the Stora is slow and smartctl can take a while */
		return disks.reduce(function(p, d) {
			return p.then(function() {
				return callSmart(d.name, wake ? '1' : '0').then(function(res) {
					self.smartCache[d.name] = res;
				}).catch(function(e) {
					self.smartCache[d.name] = { error: e.message };
				}).then(function() {
					if (self.disksNode && self.lastList)
						dom.content(self.disksNode, self.renderDisks(self.lastList));
				});
			});
		}, Promise.resolve());
	},

	showSmart: function(d, wake) {
		var self = this;
		var body = E('div', {}, E('em', { 'class': 'spinning' }, 'Reading SMART data…'));
		var close = E('button', { 'class': 'btn cbi-button', 'click': ui.hideModal }, 'Close');
		ui.showModal('SMART: ' + d.name + (d.model ? ' – ' + d.model : ''), [ body, E('div', { 'class': 'right' }, close) ]);

		var p = (wake || !this.smartCache[d.name])
			? callSmart(d.name, wake ? '1' : '0').then(function(res) { self.smartCache[d.name] = res; return res; })
			: Promise.resolve(this.smartCache[d.name]);

		p.then(function(res) {
			var sum = smartSummary(res);
			var j = sum.j || {};
			var nodes = [
				E('p', {}, [ E('strong', {}, 'Result: '),
					E('span', { 'style': 'font-weight:bold;color:' + SMART_COLORS[sum.state] }, T(sum.text)) ])
			];

			if (sum.state == 'sleep')
				nodes.push(E('p', {}, [
					T('The disk is asleep to save energy and was not woken up. '),
					E('button', { 'class': 'btn cbi-button cbi-button-action', 'click': function() { self.showSmart(d, true); } }, 'Wake up and check')
				]));

			var info = [];
			if (j.model_name) info.push([ 'Model', j.model_name ]);
			if (j.serial_number) info.push([ 'Serial number', j.serial_number ]);
			if (j.firmware_version) info.push([ 'Firmware', j.firmware_version ]);
			if (j.user_capacity && j.user_capacity.bytes) info.push([ 'Capacity', fmtSize(j.user_capacity.bytes / 512) ]);
			if (j.smart_status) info.push([ 'Overall self-assessment', j.smart_status.passed ? 'PASSED' : 'FAILED' ]);
			if (j.temperature && j.temperature.current != null) info.push([ 'Temperature', j.temperature.current + ' °C' ]);
			if (j.power_on_time && j.power_on_time.hours != null) info.push([ 'Powered on', j.power_on_time.hours + ' hours' ]);
			if (info.length)
				nodes.push(table(null, info, ''));

			var attrs = (j.ata_smart_attributes && j.ata_smart_attributes.table) || [];
			if (attrs.length) {
				nodes.push(E('h4', { 'style': 'margin-top:1em' }, 'Attributes'));
				nodes.push(E('p', {}, E('small', {}, 'The most important rows are in bold. For reallocated, pending and unreadable sectors the raw value should be 0.')));
				var t = table([ 'ID', 'Name', 'Value', 'Worst', 'Threshold', 'Raw value' ], attrs.map(function(a) {
					var failed = a.when_failed && a.when_failed != '';
					var critical = (SMART_CRITICAL[a.id] || SMART_WARN[a.id]) && smartRaw(a) > 0;
					var st = (failed || critical) ? 'color:#c00;font-weight:bold' : (SMART_HIGHLIGHT[a.id] ? 'font-weight:bold' : '');
					return [ String(a.id), a.name, String(a.value), String(a.worst), String(a.thresh),
						E('span', { 'style': st }, T(a.raw ? a.raw.string : '')) ].map(function(c, i) {
						return (i < 5 && st) ? E('span', { 'style': st }, T(c)) : c;
					});
				}), '');
				nodes.push(E('div', { 'style': 'max-height:45vh;overflow:auto' }, t));
			}

			dom.content(body, nodes);
			if (self.disksNode && self.lastList)
				dom.content(self.disksNode, self.renderDisks(self.lastList));
		}).catch(function(e) {
			dom.content(body, E('p', { 'style': 'color:#c00' }, T('Error: ' + e.message)));
		});
	},

	renderArrays: function(list) {
		var self = this;
		return table([ 'Volume', 'Type', 'Size', 'Disks', 'Status', 'Mounted on', '' ],
			list.arrays.map(function(a) {
				return [
					E('strong', {}, T(a.name + (a.label ? ' "' + a.label + '"' : ''))),
					a.level ? a.level.toUpperCase().replace('RAID', 'RAID ') : '–',
					fmtSize(a.sectors),
					a.members.join(', '),
					arrayStatus(a),
					a.mount || '–',
					E('button', {
						'class': 'btn cbi-button cbi-button-negative',
						'click': function() { self.handleRemove(a); }
					}, 'Remove')
				];
			}), 'There are no RAID volumes.');
	},

	render: function(data) {
		var self = this;
		var list = data[0] || {};
		var status = data[1] || {};

		list.disks = list.disks || [];
		list.arrays = list.arrays || [];
		list.users = list.users || [];
		list.shares = list.shares || [];

		/* --- new volume form --- */
		var radios = {};
		var modeBox = E('div', {}, Object.keys(MODES).map(function(k) {
			var needMdadm = (k != 'single');
			var disabled = needMdadm && !list.have_mdadm;
			radios[k] = E('input', {
				'type': 'radio', 'name': 'dp-mode', 'value': k,
				'checked': (k == 'single') ? true : null,
				'disabled': disabled ? true : null
			});
			return E('label', { 'style': 'display:block;margin:.4em 0;' + (disabled ? 'opacity:.5' : '') }, [
				radios[k], ' ', E('strong', {}, MODES[k].title),
				E('br'),
				E('span', { 'style': 'margin-left:1.6em;display:inline-block' },
					MODES[k].descr + (disabled ? ' (Not available: the mdadm package is missing.)' : ''))
			]);
		}));

		var checks = [];
		var diskBox = E('div', {}, list.disks.length ? list.disks.map(function(d) {
			var busy = diskBusy(d);
			var cb = E('input', { 'type': 'checkbox', 'value': d.name, 'disabled': busy ? true : null });
			checks.push({ cb: cb, disk: d });
			return E('label', { 'style': 'display:block;margin:.3em 0;' + (busy ? 'opacity:.5' : '') }, [
				cb, ' ', E('strong', {}, T(d.name)), T(' – ' + (d.model || 'unknown model') + ' – ' + fmtSize(d.sectors)),
				busy ? E('em', {}, T(' (not available: ' + busy + ')')) : ''
			]);
		}) : E('em', {}, 'No disks found.'));

		var label = E('input', { 'type': 'text', 'class': 'cbi-input-text', 'value': 'data', 'maxlength': 16 });
		var share = E('input', { 'type': 'checkbox', 'checked': list.have_ksmbd ? true : null, 'disabled': list.have_ksmbd ? null : true });
		var sharename = E('input', { 'type': 'text', 'class': 'cbi-input-text', 'value': 'data', 'maxlength': 32 });
		var shareEdited = false;
		var capacity = E('p', { 'style': 'font-weight:bold' }, '');

		var state = {
			label: label, share: share, sharename: sharename,
			mode: function() {
				for (var k in radios)
					if (radios[k].checked) return k;
				return 'single';
			},
			disks: function() {
				return checks.filter(function(c) { return c.cb.checked; }).map(function(c) { return c.disk; });
			}
		};

		var update = function() {
			var mode = state.mode(), sel = state.disks(), cfg = MODES[mode];
			if (!shareEdited)
				sharename.value = label.value.trim();
			sharename.disabled = !share.checked;
			if (sel.length < cfg.min) {
				capacity.textContent = (mode == 'single') ? 'Select one disk below.' : 'Select at least two disks below.';
				return;
			}
			if (sel.length > cfg.max) {
				capacity.textContent = 'For "Single disk", select only one disk.';
				return;
			}
			var min = Math.min.apply(null, sel.map(function(d) { return +d.sectors; }));
			var total = (mode == 'raid0') ? min * sel.length : min;
			capacity.textContent = 'Usable space: about ' + fmtSize(total);
		};
		sharename.addEventListener('input', function() { shareEdited = true; });
		[ modeBox, diskBox, label, share ].forEach(function(n) {
			n.addEventListener('change', update);
			n.addEventListener('input', update);
		});
		update();

		var missing = [];
		if (!list.have_fdisk) missing.push('fdisk');
		if (!list.have_mkfs) missing.push('e2fsprogs');

		var createForm = E('div', { 'class': 'cbi-section-node', 'style': 'padding:1em' }, [
			missing.length ? E('div', { 'class': 'alert-message warning' },
				'Missing packages: ' + missing.join(', ') + '. Install them before creating a volume.') : '',
			E('h4', {}, '1. What do you want to create?'),
			modeBox,
			E('h4', {}, '2. Which disk(s)?'),
			diskBox,
			capacity,
			E('h4', {}, '3. Name'),
			E('p', {}, [ 'Volume name: ', label, E('br'), E('small', {}, 'The volume is mounted on /mnt/&lt;name&gt;. Letters, digits, - and _ only.') ]),
			E('p', {}, [ E('label', {}, [ share, ' Share on the network right away as: ' ]), sharename ]),
			E('p', {}, E('small', {}, 'To open the share you need a user; create one below under "Network share users".')),
			E('div', { 'class': 'right' }, E('button', {
				'class': 'btn cbi-button cbi-button-positive',
				'disabled': missing.length ? true : null,
				'click': function() { self.handleCreate(state); }
			}, 'Create volume…'))
		]);

		/* --- users --- */
		var uName = E('input', { 'type': 'text', 'class': 'cbi-input-text', 'placeholder': 'name', 'autocomplete': 'off' });
		var uPw1 = E('input', { 'type': 'password', 'class': 'cbi-input-password', 'placeholder': 'password', 'autocomplete': 'new-password' });
		var uPw2 = E('input', { 'type': 'password', 'class': 'cbi-input-password', 'placeholder': 'repeat', 'autocomplete': 'new-password' });

		var users = list.have_ksmbd ? E('div', {}, [
			table([ 'User', '' ], list.users.map(function(u) {
				return [ u, E('button', { 'class': 'btn cbi-button cbi-button-negative', 'click': function() { self.handleDelUser(u); } }, 'Remove') ];
			}), 'No users yet.'),
			E('p', { 'style': 'margin-top:1em' }, [
				uName, ' ', uPw1, ' ', uPw2, ' ',
				E('button', { 'class': 'btn cbi-button cbi-button-add', 'click': function() { self.handleAddUser(uName, uPw1, uPw2); } }, 'Save')
			]),
			E('small', {}, 'If the user already exists, the password is updated.')
		]) : E('em', {}, 'Network sharing (ksmbd) is not installed.');

		var shares = table([ 'Share', 'Path on device' ], list.shares.map(function(s) {
			return [ E('strong', {}, T(s.name)), s.path || '–' ];
		}), 'No network shares yet.');

		this.lastList = list;
		var disksNode = E('div', {}, this.renderDisks(list));
		this.disksNode = disksNode;
		var arraysNode = E('div', {}, this.renderArrays(list));

		/* refresh tables every 10 s (e.g. RAID sync progress) */
		poll.add(function() {
			return callList().then(function(l) {
				l.disks = l.disks || []; l.arrays = l.arrays || [];
				self.lastList = l;
				dom.content(disksNode, self.renderDisks(l));
				dom.content(arraysNode, self.renderArrays(l));
			});
		}, 10);

		if (list.have_smart && status.state != 'running')
			window.setTimeout(function() { self.loadSmart(list.disks, false); }, 0);

		if (status.state == 'running')
			window.setTimeout(function() { self.showProgress('Task in progress'); }, 0);

		return E('div', { 'class': 'cbi-map' }, [
			E('h2', {}, 'Disks & RAID'),
			E('div', { 'class': 'cbi-map-descr' },
				'Prepare a disk for use, or combine two disks into one RAID volume, and share it on the network. ' +
				'Warning: creating a volume completely erases the selected disks.'),
			section('Disks', null, disksNode),
			section('RAID volumes', null, arraysNode),
			section('Create new volume', null, createForm),
			section('Network share users', 'Use this name and password to log in from Windows or macOS.', users),
			section('Network shares', 'Further share settings are under Services → Network Shares.', shares)
		]);
	},

	handleSave: null,
	handleSaveApply: null,
	handleReset: null
});
