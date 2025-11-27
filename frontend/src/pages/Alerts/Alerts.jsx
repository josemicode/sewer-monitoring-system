import React, { useState } from 'react';
import { useWebSocket } from '../../context/WebSocketContext';
import styles from './Alerts.module.css';

const Alerts = () => {
    const { alerts, acknowledgeAlert } = useWebSocket();
    const [hideAcknowledged, setHideAcknowledged] = useState(false);

    const activeAlerts = alerts.filter(a => !a.acknowledged);
    const ackAlerts = alerts.filter(a => a.acknowledged);

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <h1>Alert History</h1>
                <label className={styles.checkbox}>
                    <input
                        type="checkbox"
                        checked={hideAcknowledged}
                        onChange={(e) => setHideAcknowledged(e.target.checked)}
                    />
                    Hide Acknowledged
                </label>
            </div>

            {alerts.length === 0 ? (
                <div className={styles.empty}>
                    <div className={styles.emptyIcon}>✓</div>
                    <p>No alerts yet. All systems normal.</p>
                </div>
            ) : (
                <div className={styles.alertList}>
                    {/* Active Alerts */}
                    {activeAlerts.map((alert, index) => (
                        <div
                            key={`${alert.sensor_id}-${alert.timestamp}-${index}`}
                            className={styles.alertCard}
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
                                <button
                                    onClick={() => acknowledgeAlert(alert.timestamp, alert.sensor_id)}
                                    className={styles.ackButton}
                                >
                                    Acknowledge
                                </button>
                            </div>
                        </div>
                    ))}

                    {/* Acknowledged Alerts */}
                    {!hideAcknowledged && ackAlerts.map((alert, index) => (
                        <div
                            key={`${alert.sensor_id}-${alert.timestamp}-${index}`}
                            className={`${styles.alertCard} ${styles.acknowledged}`}
                        >
                            <div className={styles.alertIcon}>✓</div>
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
                                </div>
                            </div>
                            <div className={styles.actions}>
                                <span className={styles.acknowledgedBadge}>Acknowledged</span>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default Alerts;
