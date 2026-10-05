from dataclasses import dataclass


@dataclass(frozen=True)
class DemoListing:
    slug: str
    title: str
    brand: str
    model: str
    condition: str
    price_cents: int
    shipping_fee_cents: int
    fulfillment: str
    description: str
    photo: str
    is_demo: bool = True

    @property
    def photo_list(self):
        return [f'images/demos/{self.photo}']


DEMO_LISTINGS = (
    DemoListing(
        slug='ibanez-rg3250mz',
        title='Ibanez RG3250MZ Prestige',
        brand='Ibanez',
        model='RG3250MZ',
        condition='Excellent',
        price_cents=89900,
        shipping_fee_cents=1900,
        fulfillment='shipping_or_pickup',
        description='A fast-playing RG series demo listing with a bold, stage-ready finish.',
        photo='ibanez-rg3250.jpg',
    ),
    DemoListing(
        slug='jackson-dinky',
        title='Jackson Dinky JS32',
        brand='Jackson',
        model='Dinky JS32',
        condition='Very Good',
        price_cents=54900,
        shipping_fee_cents=1600,
        fulfillment='shipping',
        description='A compact superstrat-style demo listing for players who like a quick neck.',
        photo='jackson-dinky.jpg',
    ),
    DemoListing(
        slug='esp-iron-cross',
        title='ESP Iron Cross',
        brand='ESP',
        model='Iron Cross',
        condition='Excellent',
        price_cents=62900,
        shipping_fee_cents=1800,
        fulfillment='shipping_or_pickup',
        description='A single-cut demo listing with the unmistakable Iron Cross finish.',
        photo='esp-iron-cross.jpg',
    ),
    DemoListing(
        slug='schecter-c-1-classic',
        title='Schecter Hellraiser Flame',
        brand='Schecter',
        model='Hellraiser Flame',
        condition='Good',
        price_cents=72500,
        shipping_fee_cents=2100,
        fulfillment='shipping',
        description='A carved-top demo listing with a detailed, expressive look.',
        photo='schecter-hellraiser.jpg',
    ),
    DemoListing(
        slug='fender-electric',
        title='Fender Electric Guitar',
        brand='Fender',
        model='Electric Guitar',
        condition='Very Good',
        price_cents=109900,
        shipping_fee_cents=2200,
        fulfillment='shipping_or_pickup',
        description='A modern performance demo listing with a stage-inspired finish.',
        photo='fender-electric-guitar.jpg',
    ),
    DemoListing(
        slug='jackson-frankenstein',
        title='Jackson Glow in the Dark Frankenstein',
        brand='Jackson',
        model='Frankenstein',
        condition='Excellent',
        price_cents=129900,
        shipping_fee_cents=2400,
        fulfillment='shipping',
        description='A bold Jackson demo listing with a distinctive, stage-ready finish.',
        photo='jackson-frankenstein.jpg',
    ),
)


def find_demo_listing(slug):
    return next((listing for listing in DEMO_LISTINGS if listing.slug == slug), None)


def normalize_fulfillment_filter(value):
    normalized = value.casefold().strip()
    translated_values = {
        'shipping or pickup': 'shipping_or_pickup',
        'αποστολή ή παραλαβή': 'shipping_or_pickup',
        'αποστολή': 'shipping',
        'παραλαβή': 'pickup',
    }
    return translated_values.get(normalized, normalized.replace(' ', '_'))


def search_demo_listings(*, keyword='', brand='', condition='', fulfillment='', max_price=None):
    terms = (keyword.casefold(), brand.casefold(), condition.casefold())
    fulfillment_term = normalize_fulfillment_filter(fulfillment)
    matches = []
    for listing in DEMO_LISTINGS:
        searchable = ' '.join((
            listing.title, listing.description, listing.model, listing.brand,
            listing.condition, listing.fulfillment.replace('_', ' '),
        )).casefold()
        if terms[0] and terms[0] not in searchable:
            continue
        if terms[1] and terms[1] not in listing.brand.casefold():
            continue
        if terms[2] and terms[2] not in listing.condition.casefold():
            continue
        if fulfillment_term and fulfillment_term not in listing.fulfillment.casefold():
            continue
        if max_price is not None and listing.price_cents > max_price:
            continue
        matches.append(listing)
    return matches
