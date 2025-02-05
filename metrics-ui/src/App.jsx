import React, { useState, useEffect } from 'react';
import { JsonToTable } from "react-json-to-table";
import './styles.css'

export default function App() {
  const [metrics, setMetrics] = useState({});
  const [data, setData] = useState({});
  const [key, setKey] = useState('');
  const [value, setValue] = useState('');
  const [writeResult, setWriteResult] = useState('');
  const [readKey, setReadKey] = useState('');
  const [readValue, setReadValue] = useState(null);
  const [dataBoxIsChecked, setDataBoxIsChecked] = useState(false);
  const ports = [8000, 8001, 8002]; //hardcoded for now


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
          const errMsg =  { error: 'Failed to connect' }; 
          metricsData[port] = errMsg;
          allData[port] = errMsg;
        }
      }
      setMetrics(metricsData);
      setData(allData);
    };

    getMetrics();
    const interval = setInterval(getMetrics, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleWrite = async (e) => {
    e.preventDefault();
    for (const port of ports) {
      try {
        await fetch(`http://localhost:${port}/write`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({key, value})
        });
        setWriteResult("Success!")
      } catch (err) {
        setWriteResult("Failed to add!")
        console.error(`Failed to write to ${port}:`, err);
      }
    }
    setKey('');
    setValue('');
  };

  const handleRead = async (e) => {
    e.preventDefault();
    const shuffledPorts = ports.sort( () => Math.random()-0.5 ); // evenly distribute reads
    for (const port of shuffledPorts) {
      try {
        const res = await fetch(`http://localhost:${port}/read/${readKey}`);
        const val = await res.json();
        if (val !== false) {
          setReadValue(val);
          break;
        }
        else {
          setReadValue(`${readKey} does not exist`)
          break;
        }
      } catch (err) {
        console.error(`Failed to read from ${port}:`, err);
      }
    }
  };

  return (
    <div className="container">
      <div className='forms'>
        <form className="form-group" onSubmit={handleWrite}>
          <input value={key} onChange={e => setKey(e.target.value)} placeholder="Key"/>
          <input value={value} onChange={e => setValue(e.target.value)} placeholder="Value"/>
          <button>Write</button>
        </form>
        {writeResult && <div className="result">{writeResult}</div>}
    
        <form className="form-group" onSubmit={handleRead}>
          <input value={readKey} onChange={e => setReadKey(e.target.value)} placeholder="Key"/>
          <button>Read</button>
        </form>
      {readValue && <div className="result">Result: {readValue}</div>}
      <div>
      <input id="data-checkbox" type="checkbox" checked={dataBoxIsChecked} onChange={e => setDataBoxIsChecked(!dataBoxIsChecked)}/>
      <label for="data-checkbox">Show Node Data</label>
      </div>
      </div>
  
      <div className="metrics">
        {ports.map(port => (
          <div className={`node ${metrics[port]?.node?.role === 'leader' ? 'leader' : ''}`} key={port}>
            <h2 className="portTitle">Port {port}</h2>
            <div className="metrics-table">
              <JsonToTable json={metrics[port]} />
              <div className={`data-table ${dataBoxIsChecked ? 'visible' : 'hidden'}`}>
              <JsonToTable json={data[port]} />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}