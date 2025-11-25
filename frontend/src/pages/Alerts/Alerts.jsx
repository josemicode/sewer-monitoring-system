import React, { useState, useEffect } from 'react';
import { useWebSocket } from '../../context/WebSocketContext';
import { acknowledgeAlarm } from '../../api';
import styles from './Alerts.module.css';

const Alerts = () => {
    const { alerts } = useWebSocket();
    const [acknowledgedIds, setAcknowledgedIds] = useState(new Set());
    const [loading, setLoading] = useState({});

    const handleAcknowledge = async (alert, index) => {
        // Since we don't have alarm_id from WebSocket, we'll use a workaround
        // In a real app, alerts would be fetched from the backend with IDs
        setLoading({ ...loading, [index]: true });

        try {
            // For demo purposes, we'll just mark it as acknowledged locally
            // In production, you'd call: await acknowledgeAlarm(alert.id);
            setTimeout(() => {
                setAcknowledgedIds(new Set([...acknowledgedIds, index]));
                setLoading({ ...loading, [index]: false });
            }, 500);
        } catch (error) {
            console.error('Error acknowledging alarm:', error);
            setLoading({ ...loading, [index]: false });
        }
    };

    return (
        <div className={styles.container}>
            <h1>Alert History</h1>

            {alerts.length === 0 ? (
                <div className={styles.empty}>
                    <div className={styles.emptyIcon}>✓</div>
                    <p>No alerts yet. All systems normal.</p>
                </div>
            ) : (
                <div className={styles.alertList}>
                    {alerts.map((alert, index) => (
                        <div
                            key={index}
                            className={`${styles.alertCard} ${acknowledgedIds.has(index) ? styles.acknowledged : ''}`}
                        >
                            <div className={styles.alertIcon}>⚠️</div>
                            <div className={styles.alertContent}>
                                <div className={styles.alertHeader}>
                                    <h3>{alert.sensor_id?.replace('_', ' ').toUpperCase()}</h3>
                                    <span className={styles.timestamp}>
                                        {new Date(alert.timestamp).toLocaleString()}
                                    </span>
                                </div>
                                <div className={styles.alertDetails}>
                                    <div className={styles.metric}>
                                        <span className={styles.label}>Value:</span>
                                        <span className={styles.value}>{alert.value?.toFixed(2)}</span>
                                    </div>
                                    <div className={styles.metric}>
                                        <span className={styles.label}>Threshold:</span>
                                        <span className={styles.value}>{alert.threshold}</span>
                                    </div>
                                    <div className={styles.metric}>
                                        <span className={styles.label}>Exceeded by:</span>
                                        <span className={styles.valueExcess}>
                                            {((alert.value - alert.threshold) / alert.threshold * 100).toFixed(1)}%
                                        </span>
                                    </div>
                                </div>
                            </div>
                            <div className={styles.actions}>
                                {acknowledgedIds.has(index) ? (
                                    <span className={styles.acknowledgedBadge}>✓ Acknowledged</span>
                                ) : (
                                    <button
                                        onClick={() => handleAcknowledge(alert, index)}
                                        disabled={loading[index]}
                                        className={styles.ackButton}
                                    >
                                        {loading[index] ? 'Processing...' : 'Acknowledge'}
                                    </button>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default Alerts;
