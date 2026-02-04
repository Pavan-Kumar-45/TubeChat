import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button, Input } from '../components/ui';
import { Youtube, Mail, Lock, Sparkles, ArrowRight } from 'lucide-react';

export const Login = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const { register, handleSubmit, formState: { errors } } = useForm();
  const [isLoading, setIsLoading] = useState(false);
  const [serverError, setServerError] = useState('');

  const onSubmit = async (data) => {
    setIsLoading(true);
    setServerError('');
    try {
      await login(data.username, data.password);
      navigate('/');
    } catch (error) {
        setServerError(error.response?.data?.detail || "Login failed");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex bg-[#0f0f0f] relative overflow-hidden">
      {/* Animated Background Elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 left-10 w-72 h-72 bg-red-600/10 rounded-full blur-3xl animate-pulse-slow"></div>
        <div className="absolute bottom-20 right-10 w-96 h-96 bg-red-500/10 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }}></div>
        <div className="absolute top-1/2 left-1/2 w-64 h-64 bg-red-700/10 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '2s' }}></div>
      </div>

      {/* Left Side - Branding */}
      <div className="hidden lg:flex flex-1 items-center justify-center p-12 relative z-10">
        <div className="max-w-lg space-y-8 animate-slide-in-left">
          <div className="inline-flex items-center gap-3 px-4 py-2 bg-zinc-900/80 backdrop-blur-sm rounded-full border border-zinc-800 shadow-lg">
            <Sparkles className="w-5 h-5 text-yellow-500 animate-pulse" />
            <span className="text-sm font-semibold text-zinc-300">AI-Powered YouTube Insights</span>
          </div>
          
          <div>
            <div className="flex items-center gap-4 mb-4">
              <svg className="w-16 h-16" viewBox="0 0 159 110" fill="none">
                <path d="M154 17.5C154 17.5 152.5 7.5 148.5 3.5C143.5 -1.5 138 -1.5 135.5 -1.5C113 -3 79.5 -3 79.5 -3C79.5 -3 46 -3 23.5 -1.5C21 -1.5 15.5 -1.5 10.5 3.5C6.5 7.5 5 17.5 5 17.5C5 17.5 3 29.5 3 41.5V52.5C3 64.5 5 76.5 5 76.5C5 76.5 6.5 86.5 10.5 90.5C15.5 95.5 21 95.5 23.5 95.5C35.5 96.5 79.5 97 79.5 97C79.5 97 113 97 135.5 95.5C138 95.5 143.5 95.5 148.5 90.5C152.5 86.5 154 76.5 154 76.5C154 76.5 156 64.5 156 52.5V41.5C156 29.5 154 17.5 154 17.5Z" fill="#FF0000"/>
                <path d="M64 69.5L103 47L64 24.5V69.5Z" fill="white"/>
              </svg>
              <h1 className="text-5xl font-bold">
                <span className="text-white">
                  TubeChat AI
                </span>
              </h1>
            </div>
            <p className="text-xl text-zinc-400 leading-relaxed">
              Transform how you interact with YouTube content. Ask questions, get insights, and understand videos like never before.
            </p>
          </div>
        </div>
      </div>

      {/* Right Side - Login Form */}
      <div className="flex-1 flex items-center justify-center p-4 sm:p-8 relative z-10">
        <div className="w-full max-w-md animate-slide-in-right">
          <div className="bg-zinc-900/80 backdrop-blur-xl rounded-3xl p-8 sm:p-10 border border-zinc-800 shadow-2xl">
            <div className="text-center mb-8">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-red-600 text-white mb-4 shadow-lg shadow-red-500/30">
                    <svg className="w-9 h-9" viewBox="0 0 159 110" fill="none">
                      <path d="M64 69.5L103 47L64 24.5V69.5Z" fill="white"/>
                    </svg>
                </div>
                <h2 className="text-3xl font-bold text-white mb-2">Welcome Back</h2>
                <p className="text-zinc-400">Sign in to continue your journey</p>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
              <Input
                label="Username"
                icon={<Mail className="w-5 h-5" />}
                {...register('username', { required: 'Username is required' })}
                error={errors.username?.message}
                placeholder="Enter your username"
              />
              
              <Input
                label="Password"
                type="password"
                icon={<Lock className="w-5 h-5" />}
                {...register('password', { required: 'Password is required' })}
                error={errors.password?.message}
                placeholder="••••••••"
              />

              {serverError && (
                 <div className="p-4 rounded-xl bg-red-500/10 text-red-400 text-sm font-medium border border-red-500/20 animate-slide-down">
                    {serverError}
                 </div>
              )}

              <Button type="submit" className="w-full group" size="lg" isLoading={isLoading}>
                Sign In
                <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
              </Button>

              <div className="relative my-6">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-zinc-800"></div>
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-4 bg-zinc-900 text-zinc-500">New to YT-RAG?</span>
                </div>
              </div>

              <Link to="/register" className="block">
                <Button type="button" variant="secondary" className="w-full" size="lg">
                  Create Account
                </Button>
              </Link>
            </form>
          </div>
          
          <p className="text-center text-sm text-zinc-600 mt-6">
            By signing in, you agree to our Terms of Service and Privacy Policy
          </p>
        </div>
      </div>
    </div>
  );
};
