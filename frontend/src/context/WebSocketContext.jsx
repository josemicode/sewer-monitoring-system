import React, { createContext, useState, useEffect, useContext, useRef } from 'react';

const WebSocketContext = createContext(null);

export const WebSocketProvider = ({ children }) => {
    const [lastMessage, setLastMessage] = useState(null);
    const [sensors, setSensors] = useState({});
    const [isConnected, setIsConnected] = useState(false);
    const [alerts, setAlerts] = useState([]);

    // Initialize thresholds from localStorage or default
    const [thresholds, setThresholds] = useState(() => {
        try {
            const saved = localStorage.getItem('sensor_thresholds');
            return saved ? JSON.parse(saved) : {
                'sensor_0': 28.0,
                'sensor_1': 28.0,
                'sensor_2': 28.0,
                'sensor_3': 28.0
            };
        } catch (e) {
            return {
                'sensor_0': 28.0,
                'sensor_1': 28.0,
                'sensor_2': 28.0,
                'sensor_3': 28.0
            };
        }
    });

    const updateThreshold = (sensorId, value) => {
        setThresholds(prev => {
            const newThresholds = { ...prev, [sensorId]: parseFloat(value) };
            localStorage.setItem('sensor_thresholds', JSON.stringify(newThresholds));
            return newThresholds;
        });
    };

    const ws = useRef(null);
    const thresholdsRef = useRef(thresholds);

    // Keep ref in sync with state for use in event listener
    useEffect(() => {
        thresholdsRef.current = thresholds;
    }, [thresholds]);

    useEffect(() => {
        const connect = () => {
            ws.current = new WebSocket('ws://localhost:8000/ws');

            ws.current.onopen = () => {
                console.log('WebSocket Connected');
                setIsConnected(true);
            };

            ws.current.onmessage = (event) => {
                try {
                    let data = JSON.parse(event.data);

                    // Use Ref to get latest thresholds
                    const currentThresholds = thresholdsRef.current;
                    const userThreshold = currentThresholds[data.sensor_id] ?? 28.0;
                    const isUserAlert = data.value > userThreshold;

                    // Override data properties with client-side logic
                    data = {
                        ...data,
                        is_alert: isUserAlert,
                        threshold: userThreshold
                    };

                    setLastMessage(data);

                    // Update sensor state
                    setSensors((prev) => ({
                        ...prev,
                        [data.sensor_id]: {
                            value: data.value,
                            timestamp: data.timestamp || new Date().toISOString(),
                            is_alert: isUserAlert,
                            threshold: userThreshold
                        },
                    }));

                    // Handle Alerts
                    if (isUserAlert) {
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
        <WebSocketContext.Provider value={{ lastMessage, sensors, isConnected, alerts, thresholds, updateThreshold }}>
            {children}
        </WebSocketContext.Provider>
    );
};

export const useWebSocket = () => useContext(WebSocketContext);
