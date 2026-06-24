"use client";

import { useAuth } from "@/contexts/AuthContext";
import { User, Mail, Settings, Package, Heart, MapPin, CreditCard, LogOut } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function ProfilePage() {
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading || !isAuthenticated) {
    return (
      <div className="flex justify-center items-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  // Get initials for the avatar
  const initials = user?.first_name && user?.last_name 
    ? `${user.first_name[0]}${user.last_name[0]}`.toUpperCase()
    : user?.username ? user.username.substring(0, 2).toUpperCase() : "U";

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-10 max-w-5xl">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">My Account</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        
        {/* Left Sidebar - Profile Card */}
        <div className="md:col-span-1 space-y-6">
          <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm">
            {/* Header/Avatar Area */}
            <div className="bg-gradient-to-r from-blue-600 to-indigo-600 h-24"></div>
            <div className="px-6 pb-6 relative">
              <div className="absolute -top-12 left-6 h-24 w-24 bg-white rounded-full p-1 border-4 border-white shadow-md flex items-center justify-center">
                <div className="h-full w-full bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-3xl font-bold">
                  {initials}
                </div>
              </div>
              
              <div className="pt-14">
                <h2 className="text-xl font-bold text-gray-900">
                  {user?.first_name} {user?.last_name}
                </h2>
                <p className="text-sm text-gray-500 font-medium mb-4">@{user?.username}</p>
                
                <div className="flex items-center text-sm text-gray-600 bg-gray-50 p-3 rounded-lg border border-gray-100">
                  <Mail size={16} className="text-gray-400 mr-3" />
                  <span className="truncate">{user?.email}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Quick Nav */}
          <div className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm">
            <nav className="space-y-1">
              <Link href="/profile" className="flex items-center px-4 py-3 bg-blue-50 text-blue-700 font-medium rounded-xl">
                <User size={18} className="mr-3" /> Personal Information
              </Link>
              <Link href="/orders" className="flex items-center px-4 py-3 text-gray-600 hover:bg-gray-50 hover:text-gray-900 font-medium rounded-xl transition-colors">
                <Package size={18} className="mr-3" /> My Orders
              </Link>
              <Link href="/wishlist" className="flex items-center px-4 py-3 text-gray-600 hover:bg-gray-50 hover:text-gray-900 font-medium rounded-xl transition-colors">
                <Heart size={18} className="mr-3" /> Wishlist
              </Link>
              <button 
                onClick={logout}
                className="w-full flex items-center px-4 py-3 text-red-600 hover:bg-red-50 font-medium rounded-xl transition-colors"
              >
                <LogOut size={18} className="mr-3" /> Sign Out
              </button>
            </nav>
          </div>
        </div>

        {/* Right Content Area */}
        <div className="md:col-span-2 space-y-6">
          
          {/* Personal Info */}
          <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-bold text-gray-900 flex items-center">
                <User size={20} className="mr-2 text-blue-600" /> Personal Information
              </h3>
              <button className="text-sm font-medium text-blue-600 hover:underline">Edit</button>
            </div>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">First Name</label>
                <p className="text-gray-900 font-medium bg-gray-50 px-4 py-2.5 rounded-lg border border-gray-100">{user?.first_name || "-"}</p>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Last Name</label>
                <p className="text-gray-900 font-medium bg-gray-50 px-4 py-2.5 rounded-lg border border-gray-100">{user?.last_name || "-"}</p>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Username</label>
                <p className="text-gray-900 font-medium bg-gray-50 px-4 py-2.5 rounded-lg border border-gray-100">{user?.username}</p>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Email Address</label>
                <p className="text-gray-900 font-medium bg-gray-50 px-4 py-2.5 rounded-lg border border-gray-100">{user?.email}</p>
              </div>
            </div>
          </div>

          {/* Dummy Addresses */}
          <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-bold text-gray-900 flex items-center">
                <MapPin size={20} className="mr-2 text-blue-600" /> Saved Addresses
              </h3>
              <button className="text-sm font-medium text-blue-600 hover:underline">+ Add New</button>
            </div>
            
            <div className="border border-gray-200 rounded-xl p-4 flex justify-between items-start">
              <div>
                <span className="inline-block px-2.5 py-1 bg-gray-100 text-gray-600 text-xs font-bold rounded-md mb-2">HOME</span>
                <p className="font-semibold text-gray-900">{user?.first_name} {user?.last_name}</p>
                <p className="text-sm text-gray-600 mt-1">123 SmartShop Street, Tech Park</p>
                <p className="text-sm text-gray-600">Mumbai, Maharashtra - 400001</p>
              </div>
              <div className="flex gap-3">
                <button className="text-sm text-blue-600 font-medium hover:underline">Edit</button>
                <button className="text-sm text-red-500 font-medium hover:underline">Delete</button>
              </div>
            </div>
          </div>

          {/* Dummy Settings */}
          <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm">
            <h3 className="text-lg font-bold text-gray-900 flex items-center mb-6">
              <Settings size={20} className="mr-2 text-blue-600" /> Account Settings
            </h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between py-3 border-b border-gray-100">
                <div>
                  <p className="font-medium text-gray-900">Email Notifications</p>
                  <p className="text-xs text-gray-500">Receive order updates and promotions</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" defaultChecked className="sr-only peer" />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
              </div>
              <div className="flex items-center justify-between py-3">
                <div>
                  <p className="font-medium text-gray-900">Change Password</p>
                  <p className="text-xs text-gray-500">Update your account password</p>
                </div>
                <button className="px-4 py-1.5 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50">Update</button>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
