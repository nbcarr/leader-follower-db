import React, { useState, useEffect } from "react";
import "./styles.css";
import LogTable from "./LogTable";
import MetricsTable from "./MetricsTable";
import Options from "./Options";

export default function App() {
  const [dataBoxIsChecked, setDataBoxIsChecked] = useState(false);
  const [selectedPort, setSelectedPort] = useState(null);
  const ports = [8000, 8001, 8002]; //hardcoded for now
  return (
    <div className="container">
      <Options
        ports={ports}
        dataBoxIsChecked={dataBoxIsChecked}
        setDataBoxIsChecked={setDataBoxIsChecked}
      />
      <MetricsTable
        ports={ports}
        dataBoxIsChecked={dataBoxIsChecked}
        selectedPort={selectedPort}
        setSelectedPort={setSelectedPort}
      />
      <LogTable selectedPort={selectedPort} />
    </div>
  );
}
