import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white">CareerOS</h1>
          <p className="text-gray-400 mt-2">Start your AI-powered job search</p>
        </div>
        <SignUp routing="hash" />
      </div>
    </div>
  );
}
