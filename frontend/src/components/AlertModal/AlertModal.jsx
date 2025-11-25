import React, { useState, useEffect } from 'react';
import styles from './AlertModal.module.css';

const AlertModal = ({ message }) => {
    const [visible, setVisible] = useState(false);

    useEffect(() => {
        if (message) {
            setVisible(true);
            const timer = setTimeout(() => setVisible(false), 5000);
            return () => clearTimeout(timer);
        }
    }, [message]);

    if (!visible || !message) return null;

    return (
        <div className={styles.modal}>
            <div className={styles.content}>
                <div className={styles.icon}>⚠️</div>
                <div className={styles.details}>
                    <h3>Alert Triggered!</h3>
                    <p>
                        <strong>{message.sensor_id}</strong> exceeded threshold
                    </p>
                    <div className={styles.values}>
                        <span>Value: {message.value?.toFixed(2)}</span>
                        <span>Threshold: {message.threshold}</span>
                    </div>
                </div>
                <button onClick={() => setVisible(false)} className={styles.close}>
                    ×
                </button>
            </div>
        </div>
    );
};

export default AlertModal;
