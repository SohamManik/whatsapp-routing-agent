import Link from 'next/link';

export default function Dashboard() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24 relative overflow-hidden">
      {/* Background blobs for premium feel */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-blue-600/20 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-purple-600/20 blur-[120px] pointer-events-none" />
      
      <div className="z-10 max-w-5xl w-full items-center justify-center font-mono text-sm flex mb-8">
        <h1 className="text-6xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-500 to-purple-500 pb-4">
          Agentic Router
        </h1>
      </div>
      <p className="text-xl text-gray-400 max-w-2xl text-center mb-16 z-10">
        Intelligent, context-aware WhatsApp notification management powered by Nemotron 550B.
      </p>
      
      <div className="z-10 grid grid-cols-1 md:grid-cols-3 gap-8 w-full max-w-5xl">
        <div className="glass p-8 flex flex-col items-center justify-center hover:bg-white/10 hover:-translate-y-1 transition-all duration-300">
          <h2 className="text-xl font-semibold mb-2 text-gray-300">Processed</h2>
          <p className="text-5xl font-bold text-blue-400">1,248</p>
        </div>
        <div className="glass p-8 flex flex-col items-center justify-center hover:bg-white/10 hover:-translate-y-1 transition-all duration-300">
          <h2 className="text-xl font-semibold mb-2 text-gray-300">Muted</h2>
          <p className="text-5xl font-bold text-purple-400">842</p>
        </div>
        <div className="glass p-8 flex flex-col items-center justify-center hover:bg-white/10 hover:-translate-y-1 transition-all duration-300">
          <h2 className="text-xl font-semibold mb-2 text-gray-300">Notified</h2>
          <p className="text-5xl font-bold text-green-400">126</p>
        </div>
      </div>

      <div className="mt-20 z-10">
        <Link href="/feed" className="px-10 py-5 bg-gradient-to-r from-blue-600 to-purple-600 rounded-full font-bold text-xl shadow-[0_0_30px_rgba(139,92,246,0.4)] hover:shadow-[0_0_50px_rgba(139,92,246,0.6)] hover:scale-105 transition-all duration-300 inline-flex items-center gap-2">
          Open Live Feed
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
        </Link>
      </div>
    </main>
  );
}
