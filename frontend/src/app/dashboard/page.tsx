import AuthGate from '@/components/AuthGate';import DashboardApp from '@/components/DashboardApp';
export default function Dashboard(){return <AuthGate><DashboardApp/></AuthGate>}
