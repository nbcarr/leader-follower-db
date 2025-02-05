import React, { useState, useEffect } from "react";

export default function LogTable( {selectedPort} ) {
    const [logs, setLogs] = useState([])
    useEffect(() => {
        if (!selectedPort) {
          return;
        }
        
        const ws = new WebSocket(`ws://localhost:${selectedPort}/ws/logs/${selectedPort}`);
        
        ws.onopen = () => console.debug(`ws opened on ${selectedPort}`);
        ws.onclose = () => console.debug(`ws closed on ${selectedPort}`);
        ws.onmessage = (e) => {
            setLogs(prevLogs => {
              const newLogs = [...prevLogs, e.data].slice(-1000);
              return newLogs;
            });
          };
        
        return () => {
            ws.close();  
            setLogs([]);
        } 
      }, [selectedPort]);

      return (
        <div className="log-container">
          <div className="log-window">
            {logs.map((log, index) => (
              <div 
                key={index} 
                className={`log-line ${
                  log.includes('ERROR') ? 'error' :
                  log.includes('WARN') ? 'warn' :
                  log.includes('INFO') ? 'info' : ''
                }`}
              >
                {log}
              </div>
            ))}
            {!logs.length && selectedPort && (
              <div className="log-empty">Waiting for logs...</div>
            )}
            {!selectedPort && (
              <div className="log-empty">Select a node to view logs</div>
            )}
          </div>
        </div>
      );

}