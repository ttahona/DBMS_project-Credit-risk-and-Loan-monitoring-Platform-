function getToken() { return localStorage.getItem("token"); }
function getRole() { return localStorage.getItem("role"); }

function requireRole(role) {
    if (!getToken() || getRole() !== role) {
        localStorage.clear();
        globalThis.location.href = "/";
        return false;
    }
    return true;
}

function authHeaders() {
    return { "Content-Type": "application/json", "Authorization": "Bearer " + getToken() };
}

async function apiFetch(url, options = {}) {
    if (!options.headers) options.headers = authHeaders();
    const res = await fetch(url, options);
    if (res.status === 401 || res.status === 403) { logout(); return null; }
    return res;
}

function logout() {
    fetch("/auth/logout", { method: "POST", headers: authHeaders() });
    localStorage.clear();
    globalThis.location.href = "/";
}

function renderTable(containerId, rows, columns) {
    const el = document.getElementById(containerId);
    if (!rows || rows.length === 0) { el.innerHTML = "<p>No records.</p>"; return; }
    let html = "<div class='table-wrap'><table><thead><tr>" + columns.map(c => "<th>" + c.label + "</th>").join("") + "</tr></thead><tbody>";
    for (const row of rows) {
        html += "<tr>" + columns.map(c => "<td>" + (c.render ? c.render(row) : (row[c.key] ?? "")) + "</td>").join("") + "</tr>";
    }
    html += "</tbody></table></div>";
    el.innerHTML = html;
}

function statusBadge(val) {
    if (!val) return "";
    const cls = { Active: "badge-active", Pending: "badge-pending", Rejected: "badge-rejected", Completed: "badge-completed" }[val] || "";
    return `<span class="badge ${cls}">${val}</span>`;
}

function riskBadge(val) {
    if (!val) return "";
    const cls = { "Current": "risk-current", "30+ Days": "risk-30", "60+ Days": "risk-60", "90+ Days": "risk-90" }[val] || "risk-current";
    return `<span class="risk-badge ${cls}">${val}</span>`;
}

function roleBadge(val) {
    if (!val) return "";
    const cls = { borrower: "role-borrower", staff: "role-staff" }[val] || "";
    return `<span class="role-badge ${cls}">${val}</span>`;
}

function fmtCurrency(v) {
    return "৳ " + Number(v || 0).toLocaleString("en-BD", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}
