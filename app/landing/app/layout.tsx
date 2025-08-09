import type { Metadata } from 'next';
import { Figtree } from 'next/font/google';
import './globals.css';
import Footer from '@/components/footer';

const figtree = Figtree({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'AgentOps',
  description: 'The essential toolkit for ambitious AI agents',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={figtree.className}>
        <div className="px-4 py-8 md:px-16">
          {children}
          <Footer />
        </div>
      </body>
    </html>
  );
}
