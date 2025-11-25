import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import styles from './Layout.module.css';

const Layout = ({ children }) => {
    const { user, logout } = useAuth();
    const location = useLocation();

    return (
        <div className={styles.container}>
            <nav className={styles.nav}>
                <div className={styles.navContent}>
                    <h1 className={styles.logo}>Sewer Monitor</h1>
                    <div className={styles.navLinks}>
                        <Link
                            to="/dashboard"
                            className={location.pathname === '/dashboard' ? styles.active : ''}
                        >
                            Dashboard
                        </Link>
                        <Link
                            to="/alerts"
                            className={location.pathname === '/alerts' ? styles.active : ''}
                        >
                            Alerts
                        </Link>
                    </div>
                    <div className={styles.userSection}>
                        <span className={styles.username}>{user?.username}</span>
                        <button onClick={logout} className={styles.logoutBtn}>
                            Logout
                        </button>
                    </div>
                </div>
            </nav>
            <main className={styles.main}>{children}</main>
        </div>
    );
};

export default Layout;
