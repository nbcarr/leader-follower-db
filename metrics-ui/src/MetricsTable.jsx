import React, { useState, useEffect } from "react";
import { JsonToTable } from "react-json-to-table";

export default function MetricsTable({
  nodes,
  dataBoxIsChecked,
  selectedPort,
  setSelectedPort,
}) {
  const [isLeader, setIsLeader] = useState(null);
  const [metrics, setMetrics] = useState({});
  const [data, setData] = useState({});

  useEffect(() => {
    const getMetrics = async () => {
      const metricsData = {};
      const allData = {};
      for (const node of nodes) {
        try {
          const metrics = await fetch(`http://localhost:${node.port}/metrics`);
          metricsData[node.port] = await metrics.json();

          const dump = await fetch(`http://localhost:${node.port}/dump`);
          allData[node.port] = await dump.json();
        } catch (err) {
          const errMsg = { "loading...": "" };
          metricsData[node.port] = errMsg;
          allData[node.port] = errMsg;
        }
        if (metricsData[node.port]?.node?.role == "leader") {
          setIsLeader(node.port);
        }
      }

      setMetrics(metricsData);
      setData(allData);
    };

    getMetrics();
    const interval = setInterval(getMetrics, 10000);
    return () => clearInterval(interval);
  }, [nodes]);

  const handlePortSelect = (port) => {
    setSelectedPort(port === selectedPort ? null : port);
  };

  return (
    <div className="metrics">
      {nodes.map((node) => (
        <div
          className={`node ${node.port === isLeader ? "leader" : ""} 
                              ${selectedPort === node.port ? "selected" : ""}`}
          key={node.port}
          onClick={() => handlePortSelect(node.port)}
          role="button"
          tabIndex={0}
        >
          <h2 className="portTitle">
            Port {node.port} {node.port === isLeader ? "(leader)" : ""}
          </h2>
          <div className="metrics-table">
            <JsonToTable json={metrics[node.port]} />
            <div
              className={`data-table ${
                dataBoxIsChecked ? "visible" : "hidden"
              }`}
            >
              <JsonToTable json={data[node.port]} />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
