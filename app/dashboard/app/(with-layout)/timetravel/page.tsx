'use client';

// import TimeTravelTable from './_components/time-travel-table';
// // import { cookies } from 'next/headers';
// import { Tables } from '@/lib/types_db';

// // Server-side helper (copy or share)
// async function fetchServerSideApi<T = any>(_endpoint: string): Promise<T> {
//   throw new Error('not implemented');
//   // const cookieStore = await cookies();
//   // const sessionId = cookieStore.get('session_id')?.value;
//   // if (!sessionId) {
//   //   throw new Error('User is not authenticated.');
//   // }
//   // const apiUrl = process.env.NEXT_PUBLIC_API_URL;
//   // if (!apiUrl) {
//   //   throw new Error('API URL not configured.');
//   // }
//   // const targetUrl = `${apiUrl}${endpoint}`;
//   // const response = await fetch(targetUrl, {
//   //   headers: { Authorization: `Bearer ${sessionId}` },
//   //   cache: 'no-store',
//   // });
//   // if (!response.ok) {
//   //   let errorBody = `API request failed with status ${response.status}`;
//   //   try {
//   //     errorBody = await response.text();
//   //   } catch (e) {
//   //     /* ignore */
//   //   }
//   //   throw new Error(errorBody);
//   // }
//   // if (response.status === 204) return undefined as T;
//   // return response.json();
// }

export default async function TimeTravelPage() {
  return <div>Time Travel was removed, sowwy :c</div>;
//   // let ttds: Tables<'ttd'>[] = [];
//   // try {
//   //   ttds = await fetchServerSideApi<Tables<'ttd'>[]>('/timetravel'); // Assuming this endpoint
//   // } catch (error) {
//   //   console.error('Failed to fetch time travel data:', error);
//   //   // Handle error gracefully, maybe show an error message component
//   // }

//   return (
//     <div className="p-4">
//       <h1 className="mb-4 text-2xl font-bold">Time Travel Snapshots</h1>
//       {/* Render table even if fetch failed, table component might handle empty state */}
//       {/* <TimeTravelTable ttds={ttds} /> */}
//     </div>
//   );
}
