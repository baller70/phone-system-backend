
"""
Pricing engine for sports facility rentals.
Calculates rates based on time, service type, and market research data.
"""

import os
import pandas as pd
from datetime import datetime, time
from typing import Dict, Any, Optional, List
import calendar

class PricingEngine:
    """
    Handles pricing calculations for different services and time periods.
    Based on market research data and business rules.
    """
    
    def __init__(self):
        self.pricing_data = self._load_pricing_data()
        self.base_rates = self._initialize_base_rates()
        self.peak_multiplier = 1.23  # 23% increase for peak hours
        self.weekend_multiplier = 1.14  # 14% increase for weekends
        self.off_season_discount = 0.85  # 15% discount for off-season
    
    def _load_pricing_data(self) -> Optional[pd.DataFrame]:
        """Load pricing data from CSV file."""
        try:
            # Use relative path that works both locally and on Render
            base_dir = os.path.dirname(os.path.abspath(__file__))
            csv_path = os.path.join(base_dir, 'sports_facility_pricing_data.csv')
            
            if os.path.exists(csv_path):
                return pd.read_csv(csv_path)
            else:
                print(f"Warning: Pricing data file not found at {csv_path}")
                return None
        except Exception as e:
            print(f"Error loading pricing data: {e}")
            return None
    
    def _initialize_base_rates(self) -> Dict[str, Dict[str, float]]:
        """Initialize base rates based on market research."""
        return {
            'basketball': {
                'full_court': 65.0,      # Off-peak base rate
                'half_court': 45.0,      # Off-peak base rate
                'peak_full_court': 80.0,  # Peak rate
                'peak_half_court': 60.0   # Peak rate
            },
            'multi_sport': {
                'base_rate': 55.0,       # Off-peak base rate
                'peak_rate': 70.0        # Peak rate
            },
            'birthday_party': {
                'starter': 395.0,        # Up to 12 kids
                'champion': 525.0,       # Up to 16 kids
                'all_star': 675.0        # Up to 20 kids
            },
            'membership': {
                'basic': 65.0,           # Monthly, off-peak only
                'premium': 95.0,         # Monthly, all hours
                'corporate': 180.0       # Monthly, team access
            }
        }
    
    def get_pricing_info(self, service_type: str, inquiry_type: str = 'hourly') -> Dict[str, Any]:
        """
        Get pricing information for customer inquiries.
        
        Args:
            service_type: basketball, multi_sport, birthday_party, membership
            inquiry_type: hourly, package, membership
            
        Returns:
            Dictionary with pricing information and description
        """
        if service_type == 'basketball':
            return self._get_basketball_pricing(inquiry_type)
        elif service_type == 'multi_sport':
            return self._get_multi_sport_pricing(inquiry_type)
        elif service_type == 'birthday_party':
            return self._get_birthday_party_pricing()
        elif service_type == 'membership':
            return self._get_membership_pricing()
        else:
            return self._get_general_pricing()
    
    def _get_basketball_pricing(self, inquiry_type: str) -> Dict[str, Any]:
        """Get basketball court pricing information."""
        rates = self.base_rates['basketball']
        
        description = f"""
Our basketball court rental rates are:
- Off-peak hours (weekdays 9 AM to 5 PM): Full court ${rates['full_court']}/hour, Half court ${rates['half_court']}/hour
- Peak hours (weekday evenings and weekends): Full court ${rates['peak_full_court']}/hour, Half court ${rates['peak_half_court']}/hour
- Off-season flat rate (May-August): $55/hour all times
- All rentals include basic equipment and require 24-hour advance booking
        """.strip()
        
        return {
            'service_type': 'basketball',
            'rates': rates,
            'description': description,
            'peak_hours': 'Weekday evenings 5-9 PM, Weekends 9 AM-9 PM',
            'off_peak_hours': 'Weekdays 9 AM-5 PM'
        }
    
    def _get_multi_sport_pricing(self, inquiry_type: str) -> Dict[str, Any]:
        """Get multi-sport activity pricing information."""
        rates = self.base_rates['multi_sport']
        
        description = f"""
Our multi-sport activity rates are:
- Off-peak hours: ${rates['base_rate']}/hour (weekdays 9 AM to 5 PM)
- Peak hours: ${rates['peak_rate']}/hour (weekday evenings and weekends)
- Activities include dodgeball, volleyball, capture the flag, and more
- Perfect for team building, group fitness, or recreational play
        """.strip()
        
        return {
            'service_type': 'multi_sport',
            'rates': rates,
            'description': description,
            'activities': ['dodgeball', 'volleyball', 'capture_the_flag', 'soccer', 'group_fitness']
        }
    
    def _get_birthday_party_pricing(self) -> Dict[str, Any]:
        """Get birthday party package pricing information."""
        packages = self.base_rates['birthday_party']
        
        description = f"""
We offer three birthday party packages:

Starter Package - ${packages['starter']} (up to 12 kids):
- 2 hours court time with basic sports equipment
- Tables and chairs setup
- Additional children: $25 each (max 20 total)

Champion Package - ${packages['champion']} (up to 16 kids):
- 2.5 hours court time with sports coach/party host
- Choice of 2 activities plus party room for cake
- Basic decorations included
- Additional children: $30 each (max 25 total)

All-Star Package - ${packages['all_star']} (up to 20 kids):
- 3 hours court time with dedicated party coordinator
- Choice of 3 activities plus private party room
- Premium decorations and sound system
- Additional children: $32 each (max 30 total)

Add-ons available: Pizza packages, goodie bags, professional photos
        """.strip()
        
        return {
            'service_type': 'birthday_party',
            'packages': packages,
            'description': description,
            'add_ons': {
                'extra_30_minutes': 50.0,
                'pizza_package': 85.0,
                'goodie_bags': 8.0,  # per child
                'professional_photos': 150.0
            }
        }
    
    def _get_membership_pricing(self) -> Dict[str, Any]:
        """Get membership pricing information."""
        memberships = self.base_rates['membership']
        
        description = f"""
Our membership options are:

Basic Membership - ${memberships['basic']}/month:
- Off-peak hours only (weekdays 9 AM-5 PM)
- Up to 10 hours per month included
- Additional hours at 50% off regular rates
- Equipment included, no weekend access

Premium Membership - ${memberships['premium']}/month:
- All-hours access (peak and off-peak)
- Up to 15 hours per month included
- Additional hours at 30% off regular rates
- Priority booking and guest privileges

Corporate/Team Membership - ${memberships['corporate']}/month:
- Unlimited off-peak access
- 8 peak hours included per month
- Team storage space and priority booking
- 25% discount on birthday parties
        """.strip()
        
        return {
            'service_type': 'membership',
            'memberships': memberships,
            'description': description,
            'benefits': {
                'basic': ['off_peak_only', '10_hours_included', '50_percent_discount'],
                'premium': ['all_hours', '15_hours_included', '30_percent_discount', 'priority_booking'],
                'corporate': ['unlimited_off_peak', '8_peak_hours', 'team_storage', 'party_discount']
            }
        }
    
    def _get_general_pricing(self) -> Dict[str, Any]:
        """Get general pricing overview."""
        description = """
Our facility offers flexible pricing for all your sports and event needs:

Basketball Courts: $45-80/hour depending on time and court size
Multi-Sport Activities: $55-70/hour for dodgeball, volleyball, and more
Birthday Parties: Complete packages starting at $395 for up to 12 children
Memberships: Monthly options from $65-180 with included hours and discounts

We're open daily 9 AM to 9 PM with peak pricing for evenings and weekends.
All bookings require 24-hour advance notice. Equipment is included with all rentals.
        """.strip()
        
        return {
            'service_type': 'general',
            'description': description,
            'services': ['basketball', 'multi_sport', 'birthday_parties', 'memberships'],
            'hours': '9 AM - 9 PM daily'
        }
    
    def calculate_hourly_rate(self, date_time: datetime, service_type: str, 
                             court_type: str = 'full_court') -> float:
        """
        Calculate the hourly rate for a specific date/time and service.
        
        Args:
            date_time: The requested date and time
            service_type: basketball, multi_sport, etc.
            court_type: full_court, half_court (for basketball)
            
        Returns:
            Hourly rate as float
        """
        # Determine if it's peak time
        is_peak = self._is_peak_time(date_time)
        is_weekend = date_time.weekday() >= 5  # Saturday = 5, Sunday = 6
        is_off_season = self._is_off_season(date_time)
        
        # Get base rate
        if service_type == 'basketball':
            if is_peak:
                base_rate = self.base_rates['basketball'][f'peak_{court_type}']
            else:
                base_rate = self.base_rates['basketball'][court_type]
        elif service_type == 'multi_sport':
            if is_peak:
                base_rate = self.base_rates['multi_sport']['peak_rate']
            else:
                base_rate = self.base_rates['multi_sport']['base_rate']
        else:
            # Default rate
            base_rate = 65.0
        
        # Apply modifiers
        final_rate = base_rate
        
        # Off-season discount (May-August)
        if is_off_season:
            final_rate = 55.0  # Flat rate during off-season
        
        return round(final_rate, 2)
    
    def _is_peak_time(self, date_time: datetime) -> bool:
        """Determine if the given time is peak hours."""
        hour = date_time.hour
        weekday = date_time.weekday()
        
        # Weekend is always peak (Saturday = 5, Sunday = 6)
        if weekday >= 5:
            return True
        
        # Weekday evening peak hours (5 PM - 9 PM)
        if 17 <= hour < 21:
            return True
        
        return False
    
    def _is_off_season(self, date_time: datetime) -> bool:
        """Determine if the date is in off-season (May-August)."""
        month = date_time.month
        return 5 <= month <= 8
    
    def calculate_party_cost(self, package_type: str, num_children: int, 
                           add_ons: List[str] = None) -> Dict[str, Any]:
        """
        Calculate total cost for a birthday party.
        
        Args:
            package_type: starter, champion, all_star
            num_children: Number of children attending
            add_ons: List of add-on services
            
        Returns:
            Dictionary with cost breakdown
        """
        if package_type not in self.base_rates['birthday_party']:
            return {'error': 'Invalid package type'}
        
        base_cost = self.base_rates['birthday_party'][package_type]
        
        # Determine included children and additional cost per child
        package_limits = {
            'starter': {'included': 12, 'additional_cost': 25, 'max_total': 20},
            'champion': {'included': 16, 'additional_cost': 30, 'max_total': 25},
            'all_star': {'included': 20, 'additional_cost': 32, 'max_total': 30}
        }
        
        limits = package_limits[package_type]
        
        # Calculate additional children cost
        additional_children = max(0, num_children - limits['included'])
        additional_cost = additional_children * limits['additional_cost']
        
        # Check if exceeds maximum
        if num_children > limits['max_total']:
            return {
                'error': f'Maximum {limits["max_total"]} children for {package_type} package'
            }
        
        # Calculate add-ons
        addon_cost = 0
        addon_details = []
        
        if add_ons:
            addon_rates = {
                'extra_30_minutes': 50.0,
                'pizza_package': 85.0,
                'goodie_bags': 8.0 * num_children,  # Per child
                'professional_photos': 150.0
            }
            
            for addon in add_ons:
                if addon in addon_rates:
                    cost = addon_rates[addon]
                    addon_cost += cost
                    addon_details.append({
                        'item': addon.replace('_', ' ').title(),
                        'cost': cost
                    })
        
        total_cost = base_cost + additional_cost + addon_cost
        
        return {
            'package_type': package_type,
            'base_cost': base_cost,
            'num_children': num_children,
            'additional_children': additional_children,
            'additional_cost': additional_cost,
            'addon_cost': addon_cost,
            'addon_details': addon_details,
            'total_cost': total_cost,
            'breakdown': {
                'base_package': base_cost,
                'extra_children': additional_cost,
                'add_ons': addon_cost,
                'total': total_cost
            }
        }
    
    def get_membership_savings(self, monthly_hours: int, service_type: str = 'basketball') -> Dict[str, Any]:
        """Calculate potential savings with membership vs pay-per-use."""
        # Calculate pay-per-use cost (assume mix of peak/off-peak)
        avg_hourly_rate = 67.5  # Average of peak and off-peak basketball rates
        monthly_pay_per_use = monthly_hours * avg_hourly_rate
        
        memberships = self.base_rates['membership']
        
        savings_analysis = {}
        
        for membership_type, monthly_cost in memberships.items():
            if membership_type == 'basic':
                included_hours = 10
                discount_rate = 0.5  # 50% off additional hours
            elif membership_type == 'premium':
                included_hours = 15
                discount_rate = 0.7  # 30% off additional hours
            else:  # corporate
                included_hours = 8  # peak hours, unlimited off-peak
                discount_rate = 0.7
            
            # Calculate membership cost
            if monthly_hours <= included_hours:
                membership_total = monthly_cost
            else:
                extra_hours = monthly_hours - included_hours
                extra_cost = extra_hours * avg_hourly_rate * discount_rate
                membership_total = monthly_cost + extra_cost
            
            savings = monthly_pay_per_use - membership_total
            savings_percentage = (savings / monthly_pay_per_use) * 100 if monthly_pay_per_use > 0 else 0
            
            savings_analysis[membership_type] = {
                'monthly_cost': monthly_cost,
                'total_cost': membership_total,
                'savings': savings,
                'savings_percentage': round(savings_percentage, 1),
                'break_even_hours': monthly_cost / avg_hourly_rate,
                'recommended': savings > 0
            }
        
        return {
            'monthly_hours': monthly_hours,
            'pay_per_use_cost': monthly_pay_per_use,
            'membership_analysis': savings_analysis,
            'best_option': max(savings_analysis.keys(), 
                             key=lambda k: savings_analysis[k]['savings'])
        }

# Example usage and testing
if __name__ == "__main__":
    pricing_engine = PricingEngine()
    
    # Test pricing inquiries
    basketball_pricing = pricing_engine.get_pricing_info('basketball', 'hourly')
    print("Basketball Pricing:")
    print(basketball_pricing['description'])
    print("\n" + "="*50 + "\n")
    
    # Test hourly rate calculation
    test_datetime = datetime(2025, 10, 15, 18, 0)  # Tuesday 6 PM (peak)
    rate = pricing_engine.calculate_hourly_rate(test_datetime, 'basketball', 'full_court')
    print(f"Rate for {test_datetime}: ${rate}/hour")
    
    # Test party cost calculation
    party_cost = pricing_engine.calculate_party_cost('champion', 18, ['pizza_package', 'goodie_bags'])
    print(f"\nParty cost breakdown: {party_cost}")
    
    # Test membership savings
    savings = pricing_engine.get_membership_savings(12, 'basketball')
    print(f"\nMembership savings for 12 hours/month: {savings}")
