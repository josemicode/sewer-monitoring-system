import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useWebSocket } from '../../context/WebSocketContext';
import { getHistoryRaw, getHistoryAggregated } from '../../api';
import DebugPanel from '../../components/DebugPanel/DebugPanel';
import AlertModal from '../../components/AlertModal/AlertModal';
import styles from './Dashboard.module.css';

const SENSORS = ['sensor_0', 'sensor_1', 'sensor_2', 'sensor_3'];
const COLORS = ['#7c3aed', '#ec4899', '#f59e0b', '#10b981'];

const Dashboard = () => {
    const { sensors, lastMessage, thresholds, updateThreshold } = useWebSocket();
    const [timeRange, setTimeRange] = useState('-1h');
    const [historicalData, setHistoricalData] = useState({});
    const [aggregatedData, setAggregatedData] = useState([]);
    const [showAggregated, setShowAggregated] = useState(false);
    const [showNotifications, setShowNotifications] = useState(true);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        loadHistoricalData();
    }, [timeRange]);

    const loadHistoricalData = async () => {
        setLoading(true);
        try {
            // Load raw data for each sensor
            const dataPromises = SENSORS.map(sensorId =>
                getHistoryRaw(sensorId, timeRange).catch(() => [])
            );
            const results = await Promise.all(dataPromises);

            const dataMap = {};
            SENSORS.forEach((sensorId, index) => {
                dataMap[sensorId] = results[index];
            });
            setHistoricalData(dataMap);

            // Load aggregated data
            if (showAggregated) {
                const aggData = await getHistoryAggregated(timeRange, 'hour').catch(() => []);
                setAggregatedData(aggData);
            }
        } catch (error) {
            console.error('Error loading data:', error);
        }
        setLoading(false);
    };

    useEffect(() => {
        if (showAggregated) {
            loadHistoricalData();
        }
    }, [showAggregated]);

    // Prepare unified chart data
    const chartData = React.useMemo(() => {
        const dataMap = new Map();

        // Helper to add points to the map
        const addPoints = (sensorId, points) => {
            points.forEach(point => {
                // Round time to nearest second to ensure matching
                const date = new Date(point.time);
                date.setMilliseconds(0);
                const timeKey = date.toISOString();

                if (!dataMap.has(timeKey)) {
                    dataMap.set(timeKey, { time: timeKey });
                }
                dataMap.get(timeKey)[sensorId] = point.value;
            });
        };

        SENSORS.forEach(sensorId => {
            // 1. Historical Data
            const history = historicalData[sensorId] || [];
            addPoints(sensorId, history);

            // 2. Real-time Data (Current Sensor State)
            // We append the current sensor value if it's newer than the last history point
            const current = sensors[sensorId];
            if (current) {
                const lastHist = history[history.length - 1];
                if (!lastHist || new Date(current.timestamp) > new Date(lastHist.time)) {
                    addPoints(sensorId, [{ time: current.timestamp, value: current.value }]);
                }
            }
        });

        // Convert map to array and sort by time
        return Array.from(dataMap.values()).sort((a, b) => new Date(a.time) - new Date(b.time));
    }, [historicalData, sensors]);

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <h1>Sensor Dashboard</h1>
                <div className={styles.controls}>
                    <label className={styles.checkbox}>
                        <input
                            type="checkbox"
                            checked={showNotifications}
                            onChange={(e) => setShowNotifications(e.target.checked)}
                        />
                        Show Alert Notifications
                    </label>
                    <label className={styles.checkbox}>
                        <input
                            type="checkbox"
                            checked={showAggregated}
                            onChange={(e) => setShowAggregated(e.target.checked)}
                        />
                        Show Aggregated Stats
                    </label>
                    <select
                        value={timeRange}
                        onChange={(e) => setTimeRange(e.target.value)}
                        className={styles.select}
                    >
                        <option value="-1h">Last Hour</option>
                        <option value="-24h">Last Day</option>
                        <option value="-7d">Last Week</option>
                    </select>
                </div>
            </div>

            {/* Current Sensor Values */}
            <div className={styles.sensorGrid}>
                {SENSORS.map((sensorId, index) => {
                    const sensor = sensors[sensorId];
                    return (
                        <div key={sensorId} className={styles.sensorCard}>
                            <h3>{sensorId.replace('_', ' ').toUpperCase()}</h3>
                            <div className={styles.value} style={{ color: COLORS[index] }}>
                                {sensor ? sensor.value.toFixed(2) : '--'}
                            </div>

                            <div className={styles.thresholdControl}>
                                <label>Alert &gt;</label>
                                <input
                                    type="number"
                                    value={thresholds[sensorId] || 28}
                                    onChange={(e) => updateThreshold(sensorId, e.target.value)}
                                    step="0.1"
                                    className={styles.thresholdInput}
                                />
                            </div>

                            {sensor?.is_alert && (
                                <div className={styles.alertBadge}>⚠️ Alert</div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Multi-Sensor Chart */}
            <div className={styles.chartSection}>
                <h2>All Sensors - Real-time + Historical</h2>
                {loading ? (
                    <div className={styles.loading}>Loading...</div>
                ) : (
                    <ResponsiveContainer width="100%" height={400}>
                        <LineChart
                            data={chartData}
                            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                        >
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis
                                dataKey="time"
                                tickFormatter={(time) => new Date(time).toLocaleTimeString()}
                            />
                            <YAxis />
                            <Tooltip
                                labelFormatter={(time) => new Date(time).toLocaleString()}
                                formatter={(value) => value?.toFixed(2)}
                            />
                            <Legend />
                            {SENSORS.map((sensorId, index) => (
                                <Line
                                    key={sensorId}
                                    type="monotone"
                                    dataKey={sensorId}
                                    stroke={COLORS[index]}
                                    name={sensorId}
                                    dot={false}
                                    strokeWidth={2}
                                    connectNulls // Connect lines if some sensors miss a beat
                                />
                            ))}
                        </LineChart>
                    </ResponsiveContainer>
                )}
            </div>

            {/* Aggregated Stats Chart */}
            {showAggregated && aggregatedData.length > 0 && (
                <div className={styles.chartSection}>
                    <h2>Aggregated Statistics (Min/Max/Avg/Std)</h2>
                    {SENSORS.map((sensorId, index) => {
                        const sensorAggData = aggregatedData.filter(d => d.sensor_id === sensorId);
                        if (sensorAggData.length === 0) return null;

                        return (
                            <div key={sensorId} className={styles.aggChart}>
                                <h3>{sensorId.replace('_', ' ').toUpperCase()}</h3>
                                <ResponsiveContainer width="100%" height={300}>
                                    <LineChart data={sensorAggData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                                        <CartesianGrid strokeDasharray="3 3" />
                                        <XAxis
                                            dataKey="time"
                                            tickFormatter={(time) => new Date(time).toLocaleTimeString()}
                                        />
                                        <YAxis />
                                        <Tooltip
                                            labelFormatter={(time) => new Date(time).toLocaleString()}
                                            formatter={(value) => value?.toFixed(2)}
                                        />
                                        <Legend />
                                        <Line type="monotone" dataKey="min" stroke="#02fff7ff" name="Min" />
                                        <Line type="monotone" dataKey="avg" stroke={COLORS[index]} name="Avg" strokeWidth={2} />
                                        <Line type="monotone" dataKey="max" stroke="#ff0000ff" name="Max" />
                                        <Line type="monotone" dataKey="std" stroke="#a319966a" name="Std" />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        );
                    })}
                </div>
            )}

            <DebugPanel />
            {showNotifications && lastMessage?.is_alert && (
                <AlertModal message={lastMessage} />
            )}
        </div>
    );
};

export default Dashboard;
