"""
Test script for Account Deletion API
Run these tests to verify the account deletion functionality works correctly
"""

import os
import sys
import json
import requests
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from rest_framework_simplejwt.tokens import RefreshToken
from Users.models import User, UserProfile, UserAddress
from Orders.models import Order
from Cart.models import Cart

User = get_user_model()


class AccountDeletionTester:
    """Test account deletion functionality"""
    
    def __init__(self):
        self.client = Client()
        self.api_url = "http://localhost:8000/api/users"
        self.test_user = None
        self.test_token = None
    
    def setup_test_user(self):
        """Create a test user with sample data"""
        
        print("\n" + "=" * 70)
        print("SETUP: Creating test user with sample data")
        print("=" * 70)
        
        # Create user
        self.test_user = User.objects.create_user(
            email="deletetest@example.com",
            phone_number="+971501234567",
            password="TestPassword123!",
            first_name="Test",
            last_name="User"
        )
        
        # Create profile
        profile, _ = UserProfile.objects.get_or_create(
            user=self.test_user,
            defaults={
                'date_of_birth': '2000-01-01',
                'gender': 'M',
                'newsletter_subscribed': True
            }
        )
        
        # Create addresses
        for i in range(3):
            UserAddress.objects.create(
                user=self.test_user,
                street_address=f"{i+1} Test Street",
                city="Dubai",
                emirate="dubai",
                postal_code="12345",
                is_default=(i == 0)
            )
        
        # Create cart items
        for i in range(2):
            Cart.objects.create(
                user=self.test_user,
                # Add product if needed
            )
        
        # Generate JWT token
        refresh = RefreshToken.for_user(self.test_user)
        self.test_token = str(refresh.access_token)
        
        print(f"✅ Test user created")
        print(f"   Email: {self.test_user.email}")
        print(f"   Phone: {self.test_user.phone_number}")
        print(f"   User ID: {self.test_user.id}")
        print(f"   Token: {self.test_token[:20]}...")
        
        # Show sample data
        print(f"\n✅ Sample data created:")
        print(f"   • Addresses: {UserAddress.objects.filter(user=self.test_user).count()}")
        print(f"   • Cart items: {Cart.objects.filter(user=self.test_user).count()}")
        print(f"   • Profile: {UserProfile.objects.filter(user=self.test_user).exists()}")
    
    def test_get_deletion_info(self):
        """Test: GET account deletion info"""
        
        print("\n" + "=" * 70)
        print("TEST 1: Get Account Deletion Information")
        print("=" * 70)
        
        headers = {
            'Authorization': f'Bearer {self.test_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(
                f"{self.api_url}/users/account_deletion_info/",
                headers=headers
            )
            
            print(f"\n📨 Request: GET /users/account_deletion_info/")
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n✅ SUCCESS")
                print(f"   User: {data['user']['name']}")
                print(f"   Email: {data['user']['email']}")
                print(f"   Addresses: {data['related_data']['addresses']}")
                print(f"   Cart items: {data['related_data']['cart_items']}")
                print(f"   Note: {data['note']}")
                return True
            else:
                print(f"❌ FAILED: {response.text}")
                return False
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            return False
    
    def test_invalid_password(self):
        """Test: Deletion with invalid password (should fail)"""
        
        print("\n" + "=" * 70)
        print("TEST 2: Invalid Password Validation")
        print("=" * 70)
        
        headers = {
            'Authorization': f'Bearer {self.test_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'password': 'WrongPassword123!',
            'delete_method': 'soft',
            'confirm_deletion': True
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/users/request_account_deletion/",
                json=payload,
                headers=headers
            )
            
            print(f"\n📨 Request: POST /users/request_account_deletion/")
            print(f"   Password: WrongPassword123! (WRONG)")
            print(f"Status: {response.status_code}")
            
            if response.status_code == 400:
                error = response.json()
                if 'password' in error or 'detail' in error:
                    print(f"\n✅ CORRECT: Invalid password rejected")
                    print(f"   Error: {error}")
                    return True
            
            print(f"❌ FAILED: Should reject invalid password")
            return False
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            return False
    
    def test_missing_confirmation(self):
        """Test: Deletion without confirmation flag (should fail)"""
        
        print("\n" + "=" * 70)
        print("TEST 3: Missing Confirmation Flag")
        print("=" * 70)
        
        headers = {
            'Authorization': f'Bearer {self.test_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'password': 'TestPassword123!',
            'delete_method': 'soft',
            'confirm_deletion': False  # MISSING OR FALSE
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/users/request_account_deletion/",
                json=payload,
                headers=headers
            )
            
            print(f"\n📨 Request: POST /users/request_account_deletion/")
            print(f"   confirm_deletion: False (REQUIRED)")
            print(f"Status: {response.status_code}")
            
            if response.status_code == 400:
                error = response.json()
                print(f"\n✅ CORRECT: Confirmation flag required")
                print(f"   Error: {error}")
                return True
            
            print(f"❌ FAILED: Should require confirmation")
            return False
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            return False
    
    def test_soft_delete(self):
        """Test: Soft delete (anonymize account)"""
        
        print("\n" + "=" * 70)
        print("TEST 4: Soft Delete (Anonymize)")
        print("=" * 70)
        
        headers = {
            'Authorization': f'Bearer {self.test_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'password': 'TestPassword123!',
            'delete_method': 'soft',
            'confirm_deletion': True
        }
        
        original_email = self.test_user.email
        original_id = self.test_user.id
        
        try:
            response = requests.post(
                f"{self.api_url}/users/request_account_deletion/",
                json=payload,
                headers=headers
            )
            
            print(f"\n📨 Request: POST /users/request_account_deletion/")
            print(f"   delete_method: soft")
            print(f"   confirm_deletion: true")
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n✅ SUCCESS")
                print(f"   Status: {data['status']}")
                print(f"   Deletion Status: {data['deletion_status']}")
                print(f"   Deleted at: {data['deleted_at']}")
                print(f"   Message: {data['message']}")
                
                # Verify user was anonymized
                user = User.objects.get(id=original_id)
                print(f"\n✅ Verification:")
                print(f"   User is_active: {user.is_active}")
                print(f"   User deleted_at: {user.deleted_at}")
                print(f"   Email changed: {user.email != original_email}")
                print(f"   New email: {user.email}")
                
                return True
            else:
                print(f"❌ FAILED: {response.text}")
                return False
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all test cases"""
        
        print("\n" + "=" * 70)
        print("Account Deletion API - Test Suite")
        print("=" * 70)
        
        # Setup
        self.setup_test_user()
        
        # Run tests
        results = {
            'Get Deletion Info': self.test_get_deletion_info(),
            'Invalid Password': self.test_invalid_password(),
            'Missing Confirmation': self.test_missing_confirmation(),
            'Soft Delete': self.test_soft_delete(),
        }
        
        # Summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        
        print(f"\nResults: {passed}/{total} tests passed\n")
        
        for test_name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {status}: {test_name}")
        
        print("\n" + "=" * 70)
        
        if passed == total:
            print("✅ All tests passed!")
            return 0
        else:
            print(f"❌ {total - passed} test(s) failed")
            return 1


def main():
    """Main test runner"""
    
    print("""
╔═══════════════════════════════════════════════════════════════════════╗
║         Account Deletion API - Test Suite                            ║
║                                                                       ║
║  This script tests the account deletion functionality including:      ║
║  - Getting deletion information                                      ║
║  - Validating password                                               ║
║  - Requiring explicit confirmation                                   ║
║  - Soft delete (anonymization)                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
""")
    
    tester = AccountDeletionTester()
    exit_code = tester.run_all_tests()
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
