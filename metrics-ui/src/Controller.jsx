import React, { useState, useEffect, act } from "react";

export default function Controller({ activeNodes, setActiveNodes }) {
  const [newNodePort, setNewNodePort] = useState("");

  useEffect(() => {
    async function fetchNodes() {
      const response = await fetch("http://localhost:8080/nodes");
      const data = await response.json();
      console.log(data);
      setActiveNodes(data.nodes);
    }
    fetchNodes();
  }, []);

  async function addNode() {
    if (activeNodes.includes(parseInt(newNodePort))) {
      // TODO: Show error message
      return;
    }
    const peers = activeNodes.map((node) => node.port);
    const response = await fetch("http://localhost:8080/nodes/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        role: activeNodes.length === 0 ? "leader" : "follower",
        port: parseInt(newNodePort),
        peers: peers,
      }),
    });

    const data = await response.json();
    setActiveNodes([...activeNodes, data]);
  }

  async function removeNode(port) {
    await fetch("http://localhost:8080/nodes/kill", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ port }),
    });

    setActiveNodes(activeNodes.filter((node) => node.port !== port));
  }

  return (
    <div className="controller">
      <input
        type="number"
        value={newNodePort}
        min={8000}
        max={8079}
        onChange={(e) => setNewNodePort(e.target.value)}
        placeholder="New node port"
      />
      <button onClick={addNode}>Add Node</button>

      <div className="active-nodes">
        {activeNodes
          ? activeNodes.map((node) => (
              <div key={node.port}>
                Port: {node.port} | Status: {node.status} | PID: {node.pid}
                <button onClick={() => removeNode(node.port)}>Remove</button>
              </div>
            ))
          : null}
      </div>
    </div>
  );
}
