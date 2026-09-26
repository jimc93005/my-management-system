# schools_manager/context_processors.py

from .models import LandingPageConfig, FooterConfig, FooterLink


def public_site_context(request):
    """
    Makes site-wide branding and footer data available to every template
    automatically, without each view having to fetch it manually.
    Used by the public landing page, FAQ, About, and Team pages.
    """
    config = LandingPageConfig.objects.first()
    footer_config = FooterConfig.objects.first()

    footer_links = FooterLink.objects.filter(is_active=True)
    legal_links = footer_links.filter(link_type='legal')
    social_links = footer_links.filter(link_type='social')

    return {
        'config': config,
        'footer_config': footer_config,
        'legal_links': legal_links,
        'social_links': social_links,
    }