"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const backendClient_1 = require("./backendClient");
const commands_1 = require("./commands");
const sidebar_1 = require("./sidebar");
async function activate(context) {
    const backend = new backendClient_1.BackendClient(context);
    context.subscriptions.push(backend);
    const refreshViews = (0, sidebar_1.registerSidebarViews)(context, backend);
    await (0, commands_1.registerCommands)(context, backend, refreshViews);
    await refreshViews();
}
function deactivate() {
}
//# sourceMappingURL=extension.js.map