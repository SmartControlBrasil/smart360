(function () {
    const dataNode = document.getElementById("smart-system-operations-chart-data");

    if (!dataNode || typeof ApexCharts === "undefined") {
        return;
    }

    const chartData = JSON.parse(dataNode.textContent || "{}");
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const labelColor = isDark ? "#d8e2f0" : "#344054";
    const mutedColor = isDark ? "#8ea0b8" : "#667085";
    const gridColor = isDark ? "rgba(148, 163, 184, 0.16)" : "rgba(15, 23, 42, 0.08)";
    const palette = ["#38bdf8", "#22c55e", "#f59e0b", "#a78bfa"];

    const baseOptions = {
        chart: {
            foreColor: labelColor,
            toolbar: { show: false },
            animations: { enabled: true, speed: 450 },
            fontFamily: "Inter, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
        },
        dataLabels: { enabled: false },
        legend: { labels: { colors: labelColor }, fontSize: "12px" },
        tooltip: { theme: isDark ? "dark" : "light" },
        stroke: { lineCap: "round" },
    };

    function renderChart(selector, options) {
        const el = document.querySelector(selector);
        if (!el) return;
        new ApexCharts(el, options).render();
    }

    renderChart("#smart-operation-status-chart", {
        ...baseOptions,
        chart: { ...baseOptions.chart, type: "donut", height: 285 },
        series: chartData.status?.series || [],
        labels: chartData.status?.labels || [],
        colors: palette,
        stroke: { width: 0 },
        plotOptions: { pie: { donut: { size: "68%", labels: { show: true, total: { show: true, label: "OS", color: mutedColor } } } } },
    });

    renderChart("#smart-operation-mix-chart", {
        ...baseOptions,
        chart: { ...baseOptions.chart, type: "bar", height: 285 },
        series: [{ name: "Ordens", data: chartData.maintenanceMix?.series || [] }],
        colors: ["#22c55e"],
        grid: { borderColor: gridColor },
        xaxis: { categories: chartData.maintenanceMix?.labels || [], labels: { style: { colors: labelColor } } },
        yaxis: { labels: { style: { colors: mutedColor } } },
        plotOptions: { bar: { borderRadius: 7, columnWidth: "42%", distributed: true } },
        legend: { show: false },
    });

    renderChart("#smart-operation-backlog-chart", {
        ...baseOptions,
        chart: { ...baseOptions.chart, type: "area", height: 285 },
        series: [{ name: "Backlog", data: chartData.weeklyBacklog?.series || [] }],
        colors: ["#38bdf8"],
        fill: { type: "gradient", gradient: { shadeIntensity: 0.4, opacityFrom: 0.42, opacityTo: 0.04, stops: [0, 90, 100] } },
        grid: { borderColor: gridColor },
        stroke: { curve: "smooth", width: 3 },
        markers: { size: 4, strokeWidth: 0 },
        xaxis: { categories: chartData.weeklyBacklog?.labels || [], labels: { style: { colors: labelColor } }, axisBorder: { color: gridColor }, axisTicks: { color: gridColor } },
        yaxis: { labels: { style: { colors: mutedColor } } },
    });
})();
