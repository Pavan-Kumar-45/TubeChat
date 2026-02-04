import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button, Input } from '../components/ui';
import { Youtube, User, Lock, Sparkles, ArrowRight, CheckCircle } from 'lucide-react';

export const Register = () => {
    const { register: registerUser } = useAuth();
    const navigate = useNavigate();
    const { register, handleSubmit, formState: { errors } } = useForm();
    const [isLoading, setIsLoading] = useState(false);
    const [serverError, setServerError] = useState('');
  
    const onSubmit = async (data) => {
      setIsLoading(true);
      setServerError('');
      try {
        await registerUser(data.username, data.password);
        navigate('/login');
      } catch (error) {
          setServerError(error.response?.data?.detail || "Registration failed");
      } finally {
        setIsLoading(false);
      }
    };

    const features = [
      "AI-powered video insights",
      "Natural language queries",
      "Context-aware responses",
      "Chat history & bookmarks"
    ];
  
    return (
      <div className="min-h-screen flex bg-[#0f0f0f] relative overflow-hidden">
        {/* Animated Background */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-20 right-10 w-72 h-72 bg-red-600/10 rounded-full blur-3xl animate-pulse-slow"></div>
          <div className="absolute bottom-20 left-10 w-96 h-96 bg-red-500/10 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }}></div>
          <div className="absolute top-1/2 right-1/3 w-64 h-64 bg-red-700/10 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '2s' }}></div>
        </div>

        {/* Left Side - Form */}
        <div className="flex-1 flex items-center justify-center p-4 sm:p-8 relative z-10">
          <div className="w-full max-w-md animate-slide-in-left">
            <div className="bg-zinc-900/80 backdrop-blur-xl rounded-3xl p-8 sm:p-10 border border-zinc-800 shadow-2xl">
              <div className="text-center mb-8">
                  <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-red-600 text-white mb-4 shadow-lg shadow-red-500/30 animate-pulse-slow">
                      <svg className="w-9 h-9" viewBox="0 0 159 110" fill="none">
                        <path d="M64 69.5L103 47L64 24.5V69.5Z" fill="white"/>
                      </svg>
                  </div>
                  <h2 className="text-3xl font-bold text-white mb-2">Join TubeChat AI</h2>
                  <p className="text-zinc-400">Create your account to get started</p>
              </div>
    
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
                <Input
                  label="Username"
                  icon={<User className="w-5 h-5" />}
                  {...register('username', { 
                    required: 'Username is required', 
                    minLength: { value: 3, message: 'Minimum 3 characters' } 
                  })}
                  error={errors.username?.message}
                  placeholder="Choose a username"
                />
                
                <Input
                  label="Password"
                  type="password"
                  icon={<Lock className="w-5 h-5" />}
                  {...register('password', { 
                    required: 'Password is required', 
                    minLength: { value: 6, message: 'Minimum 6 characters' } 
                  })}
                  error={errors.password?.message}
                  placeholder="Create a secure password"
                />
    
                {serverError && (
                   <div className="p-4 rounded-xl bg-red-500/10 text-red-400 text-sm font-medium border border-red-500/20 animate-slide-down">
                      {serverError}
                   </div>
                )}
    
                <Button type="submit" className="w-full group" size="lg" isLoading={isLoading}>
                  Create Account
                  <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
                </Button>

                <div className="relative my-6">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-zinc-800"></div>
                  </div>
                  <div className="relative flex justify-center text-sm">
                    <span className="px-4 bg-zinc-900 text-zinc-500">Already have an account?</span>
                  </div>
                </div>

                <Link to="/login" className="block">
                  <Button type="button" variant="secondary" className="w-full" size="lg">
                    Sign In Instead
                  </Button>
                </Link>
              </form>
            </div>
            
            <p className="text-center text-sm text-zinc-600 mt-6">
              By creating an account, you agree to our Terms & Privacy Policy
            </p>
          </div>
        </div>

        {/* Right Side - Features */}
        <div className="hidden lg:flex flex-1 items-center justify-center p-12 relative z-10">
          <div className="max-w-lg space-y-8 animate-slide-in-right">
            <div className="inline-flex items-center gap-3 px-4 py-2 bg-zinc-900/80 backdrop-blur-sm rounded-full border border-zinc-800 shadow-lg">
              <Sparkles className="w-5 h-5 text-yellow-500 animate-pulse" />
              <span className="text-sm font-semibold text-zinc-300">Start Your Free Journey</span>
            </div>
            
            <div>
              <h2 className="text-5xl font-bold mb-4 text-white">
                Everything you need to master 
                <span className="text-red-500"> YouTube content</span>
              </h2>
              <p className="text-lg text-zinc-400 leading-relaxed">
                Unlock the power of AI to understand, analyze, and interact with any YouTube video.
              </p>
            </div>

            <div className="space-y-4 pt-4">
              {features.map((feature, index) => (
                <div 
                  key={index}
                  className="flex items-center gap-4 p-4 bg-zinc-900/60 backdrop-blur-sm rounded-2xl border border-zinc-800 animate-slide-up"
                  style={{ animationDelay: `${index * 100}ms` }}
                >
                  <div className="flex-shrink-0 w-10 h-10 rounded-full bg-red-600 flex items-center justify-center shadow-lg">
                    <CheckCircle className="w-5 h-5 text-white" />
                  </div>
                  <p className="font-medium text-zinc-200">{feature}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  };
