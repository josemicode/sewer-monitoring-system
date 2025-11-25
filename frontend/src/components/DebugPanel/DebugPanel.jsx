import React, { useState } from 'react';
import { useWebSocket } from '../../context/WebSocketContext';
import styles from './DebugPanel.module.css';

const DebugPanel = () => {
    const { lastMessage, isConnected } = useWebSocket();
    const [isOpen, setIsOpen] = useState(false);

    if (!isOpen) {
        return (
            <button className={styles.toggle} onClick={() => setIsOpen(true)}>
                Debug
            </button>
        );
    }

    return (
        <div className={styles.panel}>
            <div className={styles.header}>
                <h3>Debug Panel</h3>
                <button onClick={() => setIsOpen(false)}>Close</button>
            </div>
            <div className={styles.status}>
                Status: <span className={isConnected ? styles.connected : styles.disconnected}>
                    {isConnected ? 'Connected' : 'Disconnected'}
                </span>
            </div>
            <div className={styles.content}>
                <pre>{JSON.stringify(lastMessage, null, 2)}</pre>
            </div>
        </div>
    );
};

export default DebugPanel;
