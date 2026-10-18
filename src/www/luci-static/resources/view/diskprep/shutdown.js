'use strict';
'require view';
'require rpc';
'require ui';

var callPoweroff = rpc.declare({ object: 'luci.diskprep', method: 'poweroff' });

return view.extend({
	handleShutdown: function() {
		ui.showModal('Shut down the device?', [
			E('p', {}, 'The network shares will be unavailable until you switch the device on again with its power button.'),
			E('div', { 'class': 'right' }, [
				E('button', { 'class': 'btn cbi-button', 'click': ui.hideModal }, 'Cancel'), ' ',
				E('button', {
					'class': 'btn cbi-button cbi-button-negative',
					'click': function() {
						callPoweroff().then(function() {
							ui.showModal('Shutting down…', [
								E('p', { 'class': 'spinning' }, 'The device is shutting down. This takes about half a minute; the disks and the fan stop when it is done.'),
								E('p', {}, 'To switch it on again, press the power button.')
							]);
						}).catch(function(e) {
							ui.hideModal();
							ui.addNotification(null, E('p', {}, 'Error: ' + e.message), 'danger');
						});
					}
				}, 'Shut down')
			])
		]);
	},

	render: function() {
		return E('div', { 'class': 'cbi-map' }, [
			E('h2', {}, 'Shut down'),
			E('div', { 'class': 'cbi-map-descr' }, 'Safely shut down and switch off the device. Pressing the power button does the same.'),
			E('div', { 'class': 'cbi-section' }, [
				E('button', { 'class': 'btn cbi-button cbi-button-negative', 'click': ui.createHandlerFn(this, 'handleShutdown') }, 'Shut down…')
			])
		]);
	},

	handleSave: null,
	handleSaveApply: null,
	handleReset: null
});
