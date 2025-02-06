import React, { useState, useEffect, act } from "react";
import "./styles.css";
import LogTable from "./LogTable";
import MetricsTable from "./MetricsTable";
import Options from "./Options";
import Controller from "./Controller";

export default function App() {
  const [dataBoxIsChecked, setDataBoxIsChecked] = useState(false);
  const [selectedPort, setSelectedPort] = useState(null);
  const [activeNodes, setActiveNodes] = useState([]);

  return (
    <div className="container">
      <Options
        nodes={activeNodes}
        dataBoxIsChecked={dataBoxIsChecked}
        setDataBoxIsChecked={setDataBoxIsChecked}
      />
      <Controller activeNodes={activeNodes} setActiveNodes={setActiveNodes} />
      <MetricsTable
        nodes={activeNodes}
        dataBoxIsChecked={dataBoxIsChecked}
        selectedPort={selectedPort}
        setSelectedPort={setSelectedPort}
      />
      <LogTable selectedPort={selectedPort} />
    </div>
  );
}
