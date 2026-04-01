from flask import Flask, jsonify, render_template_string, request
import pandas as pd
from pulp import LpProblem, LpMaximize, LpVariable, lpSum, value, PULP_CBC_CMD

app = Flask(__name__)
EXCEL_FILE = "production_data_upgraded.xlsx"

BASE_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Manufacturing Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; padding: 24px; background: #f4f7fb; color: #1f2937; }
    header { margin-bottom: 24px; }
    h1 { margin: 0; font-size: 28px; }
    .card { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 10px 30px rgba(15,23,42,0.08); margin-bottom: 20px; }
    .grid { display: grid; gap: 20px; }
    .grid-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    label { display: block; margin-bottom: 8px; font-weight: 600; }
    input[type=number] { width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px; }
    button { padding: 12px 18px; font-size: 14px; border: none; border-radius: 8px; background: #2563eb; color: white; cursor: pointer; }
    button:hover { background: #1d4ed8; }
    table { width: 100%; border-collapse: collapse; margin-top: 16px; }
    th, td { text-align: left; padding: 10px; border-bottom: 1px solid #e5e7eb; }
    th { background: #eef2ff; }
  </style>
</head>
<body>
  <header>
    <h1>Manufacturing Optimization Dashboard</h1>
    <p>Live resource-control dashboard for <code>product.py</code> data.</p>
  </header>

  <div class="card">
    <div class="grid grid-2">
      <div>
        <label for="labor_limit">Labor Limit</label>
        <input type="number" id="labor_limit" value="100" min="0" step="1">
      </div>
      <div>
        <label for="machine_limit">Machine Limit</label>
        <input type="number" id="machine_limit" value="80" min="0" step="1">
      </div>
      <div>
        <label for="material_limit">Material Limit</label>
        <input type="number" id="material_limit" value="60" min="0" step="1">
      </div>
      <div style="align-self:flex-end;">
        <button id="update-button">Update Dashboard</button>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>Summary</h2>
    <div id="summary"></div>
  </div>

  <div class="card">
    <h2>Optimal Production Plan</h2>
    <canvas id="productionChart"></canvas>
  </div>

  <div class="grid grid-2">
    <div class="card">
      <h2>Profit Contribution</h2>
      <canvas id="profitChart"></canvas>
    </div>
    <div class="card">
      <h2>Resource Utilization</h2>
      <canvas id="resourceChart"></canvas>
    </div>
  </div>

  <div class="card">
    <h2>Production Details</h2>
    <table>
      <thead>
        <tr><th>Product</th><th>Produced</th><th>Profit</th><th>Labor</th><th>Machine</th><th>Material</th><th>Max Demand</th></tr>
      </thead>
      <tbody id="details"></tbody>
    </table>
  </div>

  <script>
    const productionCtx = document.getElementById('productionChart').getContext('2d');
    const profitCtx = document.getElementById('profitChart').getContext('2d');
    const resourceCtx = document.getElementById('resourceChart').getContext('2d');

    let productionChart, profitChart, resourceChart;

    async function fetchDashboard(labor, machine, material) {
      const res = await fetch(`/api/solve?labor=${labor}&machine=${machine}&material=${material}`);
      return res.json();
    }

    function renderSummary(data) {
      const html = `
        <p><strong>Maximum Profit:</strong> ₹${data.total_profit.toFixed(2)}</p>
        <p><strong>Labor:</strong> ${data.labor_used.toFixed(2)}/${data.labor_limit}</p>
        <p><strong>Machine:</strong> ${data.machine_used.toFixed(2)}/${data.machine_limit}</p>
        <p><strong>Material:</strong> ${data.material_used.toFixed(2)}/${data.material_limit}</p>
      `;
      document.getElementById('summary').innerHTML = html;
    }

    function renderDetails(data) {
      const rows = data.products.map((product, index) => `
        <tr>
          <td>${product}</td>
          <td>${data.production_values[index].toFixed(2)}</td>
          <td>₹${data.profits[index].toFixed(2)}</td>
          <td>${data.labor_usage[index].toFixed(2)}</td>
          <td>${data.machine_usage[index].toFixed(2)}</td>
          <td>${data.material_usage[index].toFixed(2)}</td>
          <td>${data.max_demand[index]}</td>
        </tr>
      `).join('');
      document.getElementById('details').innerHTML = rows;
    }

    function renderCharts(data) {
      const labels = data.products;
      const productionData = data.production_values;
      const profitData = data.profits;
      const resourceData = [data.labor_used, data.machine_used, data.material_used];

      if (productionChart) productionChart.destroy();
      productionChart = new Chart(productionCtx, {
        type: 'bar',
        data: { labels, datasets: [{ label: 'Units Produced', data: productionData, backgroundColor: '#3b82f6' }] },
        options: { responsive: true, scales: { y: { beginAtZero: true } } }
      });

      if (profitChart) profitChart.destroy();
      profitChart = new Chart(profitCtx, {
        type: 'bar',
        data: { labels, datasets: [{ label: 'Profit Contribution', data: profitData, backgroundColor: '#10b981' }] },
        options: { responsive: true, scales: { y: { beginAtZero: true } } }
      });

      if (resourceChart) resourceChart.destroy();
      resourceChart = new Chart(resourceCtx, {
        type: 'bar',
        data: { labels: ['Labor', 'Machine', 'Material'], datasets: [{ label: 'Used', data: resourceData, backgroundColor: ['#f59e0b','#8b5cf6','#ef4444'] }] },
        options: { responsive: true, scales: { y: { beginAtZero: true } } }
      });
    }

    async function updateDashboard() {
      const labor = document.getElementById('labor_limit').value;
      const machine = document.getElementById('machine_limit').value;
      const material = document.getElementById('material_limit').value;
      const data = await fetchDashboard(labor, machine, material);
      renderSummary(data);
      renderDetails(data);
      renderCharts(data);
    }

    document.getElementById('update-button').addEventListener('click', updateDashboard);
    updateDashboard();
  </script>
</body>
</html>
"""


def load_data():
    return pd.read_excel(EXCEL_FILE)


def solve_model(labor_limit: float, machine_limit: float, material_limit: float):
    df = load_data()
    products = df['Product'].tolist()

    model = LpProblem('Smart_Manufacturing_Optimizer', LpMaximize)
    x = LpVariable.dicts('Production', products, lowBound=0)

    model += lpSum(df.loc[i, 'Profit'] * x[products[i]] for i in range(len(products)))
    model += lpSum(df.loc[i, 'Labor'] * x[products[i]] for i in range(len(products))) <= labor_limit
    model += lpSum(df.loc[i, 'Machine'] * x[products[i]] for i in range(len(products))) <= machine_limit
    model += lpSum(df.loc[i, 'Material'] * x[products[i]] for i in range(len(products))) <= material_limit

    for i in range(len(products)):
        model += x[products[i]] <= df.loc[i, 'Max_Demand']

    model.solve(PULP_CBC_CMD(msg=False))

    production_values = [x[p].varValue for p in products]
    profits = [production_values[i] * df.loc[i, 'Profit'] for i in range(len(products))]
    labor_usage = [production_values[i] * df.loc[i, 'Labor'] for i in range(len(products))]
    machine_usage = [production_values[i] * df.loc[i, 'Machine'] for i in range(len(products))]
    material_usage = [production_values[i] * df.loc[i, 'Material'] for i in range(len(products))]

    return {
        'products': products,
        'production_values': production_values,
        'profits': profits,
        'labor_usage': labor_usage,
        'machine_usage': machine_usage,
        'material_usage': material_usage,
        'max_demand': df['Max_Demand'].tolist(),
        'labor_used': sum(labor_usage),
        'machine_used': sum(machine_usage),
        'material_used': sum(material_usage),
        'labor_limit': labor_limit,
        'machine_limit': machine_limit,
        'material_limit': material_limit,
        'total_profit': value(model.objective)
    }


@app.route('/')
def index():
    return render_template_string(BASE_TEMPLATE)


@app.route('/api/solve')
def api_solve():
    labor = float(request.args.get('labor', 100))
    machine = float(request.args.get('machine', 80))
    material = float(request.args.get('material', 60))
    out = solve_model(labor, machine, material)
    return jsonify(out)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
