import React, { useState, useEffect } from "react";
import { JsonToTable } from "react-json-to-table";

export default function MetricsTable( { ports, dataBoxIsChecked, selectedPort, setSelectedPort }) {
    const [isLeader, setIsLeader] = useState(null);
    const [metrics, setMetrics] = useState({});
    const [data, setData] = useState({});

    useEffect(() => {
        const getMetrics = async () => {
          const metricsData = {};
          const allData = {};
          for (const port of ports) {
            try {
              const metrics = await fetch(`http://localhost:${port}/metrics`);
              metricsData[port] = await metrics.json();
    
              const dump = await fetch(`http://localhost:${port}/dump`);
              allData[port] = await dump.json();
            } catch (err) {
              const errMsg = { error: "Failed to connect" };
              metricsData[port] = errMsg;
              allData[port] = errMsg;
            }
            if (metricsData[port]?.node?.role == "leader") {
              setIsLeader(port);
            }
          }
    
          setMetrics(metricsData);
          setData(allData);
        };
    
        getMetrics();
        const interval = setInterval(getMetrics, 10000);
        return () => clearInterval(interval);
      }, []);

    const handlePortSelect = (port) => {
        setSelectedPort(port === selectedPort ? null : port);
      };

    return (
        <div className="metrics">
        {ports.map((port) => (
          <div
            className={`node ${port === isLeader ? "leader" : ""} 
                              ${selectedPort === port ? "selected" : ""}`}
            key={port}
            onClick={() => handlePortSelect(port)}
            role="button"
            tabIndex={0}
          >
            <h2 className="portTitle">
              Port {port} {port === isLeader ? "(leader)" : ""}
            </h2>
            <div className="metrics-table">
              <JsonToTable json={metrics[port]} />
              <div
                className={`data-table ${
                  dataBoxIsChecked ? "visible" : "hidden"
                }`}
              >
                <JsonToTable json={data[port]} />
              </div>
            </div>
          </div>
        ))}
      </div>
    )
}