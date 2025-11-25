import React, { createContext, useState, useEffect, useContext, useRef } from 'react';

const WebSocketContext = createContext(null);

export const WebSocketProvider = ({ children }) => {
    const [lastMessage, setLastMessage] = useState(null);
    const [sensors, setSensors] = useState({});
    const [isConnected, setIsConnected] = useState(false);
    const [alerts, setAlerts] = useState([]);
    const ws = useRef(null);

    useEffect(() => {
        const connect = () => {
            ws.current = new WebSocket('ws://localhost:8000/ws');

            ws.current.onopen = () => {
                console.log('WebSocket Connected');
                setIsConnected(true);
            };

            ws.current.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    setLastMessage(data);

                    // Update sensor state
                    setSensors((prev) => ({
                        ...prev,
                        [data.sensor_id]: {
                            value: data.value,
                            timestamp: data.timestamp || new Date().toISOString(),
                            is_alert: data.is_alert,
                            threshold: data.threshold
                        },
                    }));

                    // Handle Alerts
                    if (data.is_alert) {
                        setAlerts((prev) => {
                            // Avoid duplicate alerts for the same sensor if very close in time? 
                            // For now, I'll insert on the front. We can filter in UI (or not).
                            return [data, ...prev].slice(0, 50); // Keep last 50
                        });
                    }

                } catch (err) {
                    console.error('Error parsing WS message:', err);
                }
            };

            ws.current.onclose = () => {
                console.log('WebSocket Disconnected');
                setIsConnected(false);
                // Retry connection
                setTimeout(connect, 3000);
            };

            ws.current.onerror = (error) => {
                console.error('WebSocket Error:', error);
                ws.current.close();
            };
        };

        connect();

        return () => {
            if (ws.current) {
                ws.current.close();
            }
        };
    }, []);

    return (
        <WebSocketContext.Provider value={{ lastMessage, sensors, isConnected, alerts }}>
            {children}
        </WebSocketContext.Provider>
    );
};

export const useWebSocket = () => useContext(WebSocketContext);
