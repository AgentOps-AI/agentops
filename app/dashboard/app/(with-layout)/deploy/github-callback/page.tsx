"use client"
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

export default function GithubCallbackPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const url = new URL(window.location.href);
    const code = url.searchParams.get('code');
    if (!code) {
      setError('Missing code parameter from GitHub.');
      setLoading(false);
      return;
    }
    // Retrieve projectId from localStorage
    const projectId = localStorage.getItem('github_connect_project_id');
    if (!projectId) {
      setError('Missing projectId from local storage.');
      setLoading(false);
      return;
    }
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) {
      throw new Error('API URL not configured');
    }
    fetch(`${apiUrl}/deploy/github/auth?code=${encodeURIComponent(code)}&project_id=${encodeURIComponent(projectId)}`, {
      credentials: 'include',
    })
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json();
          throw new Error(data.error || 'OAuth callback failed');
        }
        localStorage.removeItem('github_connect_project_id');
        router.replace(`/deploy/${projectId}/setup`);
      })
      .catch((err) => {
        setError(err.message || 'OAuth callback failed');
        setLoading(false);
      });
  }, [router]);

  if (loading) {
    return <div className="flex flex-col items-center justify-center min-h-screen">Connecting to GitHub...</div>;
  }
  if (error) {
    return <div className="flex flex-col items-center justify-center min-h-screen text-red-500">{error}</div>;
  }
  return null;
} 