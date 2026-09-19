import AuthGate from '@/components/AuthGate';import DashboardApp from '@/components/DashboardApp';
export default function Onboarding(){return <AuthGate><DashboardApp onboarding/></AuthGate>}
