import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'Job Hunter — Focus your search. Make your move.', description: 'Find relevant jobs, prioritize your best matches, and create tailored resumes and outreach. Your job search, organized in one local workspace.' };
export default function RootLayout({children}:Readonly<{children:React.ReactNode}>){return <html lang="en"><body>{children}</body></html>}
