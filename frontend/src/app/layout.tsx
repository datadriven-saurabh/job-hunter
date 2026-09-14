import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'AutoCareer — Your next chapter', description: 'Your private, local career workspace. Discover opportunities, prepare applications, and practice interviews.' };
export default function RootLayout({children}:Readonly<{children:React.ReactNode}>){return <html lang="en"><body>{children}</body></html>}
