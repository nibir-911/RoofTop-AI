import { useState, useEffect } from 'react'
import { useAppStore } from '../store/useAppStore'
import { getSuppliers, getProducts, createOrder, simulateWebhook, withFallback, MOCK } from '../services/api'
import { VERIFIED_50_MARKETPLACE } from '../data/verified50Marketplace'
import {
  ChevronRight,
  ChevronLeft,
  ShoppingBag,
  Plus,
  Minus,
  Trash2,
  CheckCircle2,
  ShieldCheck,
  CreditCard,
  Truck,
  ExternalLink,
  Store,
  Tag,
  Package
} from 'lucide-react'

export default function Suppliers({ onNext, onBack }) {
  const {
    sessionId,
    cart,
    addToCart,
    removeFromCart,
    clearCart,
    orders,
    addOrder,
  } = useAppStore()

  const [suppliers, setSuppliers] = useState([])
  const [products, setProducts] = useState(VERIFIED_50_MARKETPLACE)
  const [categoryFilter, setCategoryFilter] = useState('All')
  const [loading, setLoading] = useState(false)
  const [checkoutLoading, setCheckoutLoading] = useState(false)
  const [paymentMethod, setPaymentMethod] = useState('cod')
  const [lastOrder, setLastOrder] = useState(null)
  const [webhookStatus, setWebhookStatus] = useState(null)

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        const supRes = await withFallback(() => getSuppliers(), MOCK.suppliers)
        setSuppliers(supRes)

        const prodRes = await withFallback(
          () => getProducts(),
          VERIFIED_50_MARKETPLACE
        )
        setProducts(prodRes)
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  const cartTotal = cart.reduce((sum, item) => sum + (item.qty * (item.unit_price_bdt || item.price_bdt || 0)), 0)

  const filteredProducts = products.filter(p => {
    if (categoryFilter === 'All') return true
    const cat = (p.category || '').toLowerCase()
    if (categoryFilter === 'Growing Media') return cat.includes('media') || cat.includes('soil')
    if (categoryFilter === 'Pot & Grow Bag') return cat.includes('pot') || cat.includes('grow bag') || cat.includes('planter')
    if (categoryFilter === 'Compost') return cat.includes('compost') || cat.includes('fertilizer') || cat.includes('care')
    if (categoryFilter === 'Seed & Plants') return cat.includes('seed') || cat.includes('plant')
    if (categoryFilter === 'Tool & Hardware') return cat.includes('tool') || cat.includes('accessory') || cat.includes('irrigation')
    return true
  })

  const handleCheckout = async () => {
    if (cart.length === 0) return
    setCheckoutLoading(true)
    try {
      const orderPayload = {
        project_id: sessionId || 'demo-project',
        payment_method: paymentMethod,
        items: cart.map(c => ({
          product_id: c.product_id || c.id,
          name: c.name,
          qty: c.qty,
          unit_price_bdt: c.unit_price_bdt || c.price_bdt || 0,
        }))
      }

      const res = await withFallback(
        () => createOrder(orderPayload),
        {
          order_id: `ord_${Math.random().toString(36).slice(2, 8)}`,
          status: paymentMethod === 'sandbox' ? 'pending_payment' : 'confirmed',
          total_bdt: cartTotal,
          sandbox_token: paymentMethod === 'sandbox' ? `tok_${Date.now()}` : null
        }
      )

      setLastOrder(res)
      addOrder(res)
      clearCart()
    } catch (e) {
      console.error(e)
    } finally {
      setCheckoutLoading(false)
    }
  }

  const handleSimulatePayment = async () => {
    if (!lastOrder?.order_id) return
    try {
      await withFallback(
        () => simulateWebhook(lastOrder.order_id, { sandbox_token: lastOrder.sandbox_token, event: 'payment_success' }),
        { status: 'success', order_status: 'paid' }
      )
      setWebhookStatus('Payment Verified & Order Confirmed!')
      setLastOrder({ ...lastOrder, status: 'paid' })
    } catch (e) {
      setWebhookStatus('Payment simulation completed.')
    }
  }

  return (
    <div className="space-y-6">
      {/* Verified Local Suppliers Grid */}
      <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm space-y-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-700">Verified Partner Network</span>
          </div>
          <h2 className="text-xl font-bold text-slate-900 mt-0.5">Verified Bangladeshi Suppliers &amp; Nurseries</h2>
          <p className="text-sm text-slate-500">Source certified seeds, growing media, UV-treated pots, and rooftop gardening equipment with direct store links.</p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {suppliers.map(s => (
            <div key={s.id} className="rounded-xl border border-slate-200 bg-slate-50/50 p-4 space-y-2.5 flex flex-col justify-between hover:border-emerald-300 transition">
              <div className="space-y-1.5">
                <div className="flex items-center justify-between gap-1">
                  <span className="text-[10px] font-bold text-emerald-800 bg-emerald-100/70 border border-emerald-200 px-2 py-0.5 rounded-full uppercase tracking-wider">
                    {s.supplier_type || s.category}
                  </span>
                  {s.verified && (
                    <span className="flex items-center text-[10px] text-emerald-600 font-semibold gap-1 shrink-0">
                      <ShieldCheck className="h-3.5 w-3.5" /> Verified
                    </span>
                  )}
                </div>
                <h4 className="font-bold text-sm text-slate-900">{s.name}</h4>
                <p className="text-xs text-slate-500 line-clamp-2">{s.area}</p>
                {s.contact && <p className="text-xs text-slate-400 font-mono">{s.contact}</p>}
                {s.product_categories && (
                  <p className="text-[11px] text-slate-500 line-clamp-1">Categories: {s.product_categories}</p>
                )}
              </div>
              {(s.website_or_page || s.source_url) && (
                <a
                  href={s.website_or_page || s.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-1 inline-flex items-center justify-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50/70 px-3 py-1.5 text-xs font-semibold text-emerald-800 hover:bg-emerald-100 transition"
                >
                  <Store className="h-3.5 w-3.5" /> Visit Supplier Website <ExternalLink className="h-3 w-3 opacity-70" />
                </a>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
        {/* Product Catalog */}
        <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-100 pb-3">
            <div>
              <h3 className="font-bold text-slate-900">Gardening Essentials Catalog</h3>
              <p className="text-xs text-slate-500">Live prices in Bangladeshi Taka (BDT) from verified regional stores.</p>
            </div>
            <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200 shrink-0 self-start sm:self-auto">
              {filteredProducts.length} Items Available
            </span>
          </div>

          {/* Category Filter Pills */}
          <div className="flex flex-wrap gap-1.5 pt-0.5">
            {['All', 'Growing Media', 'Pot & Grow Bag', 'Compost', 'Seed & Plants', 'Tool & Hardware'].map(cat => (
              <button
                key={cat}
                onClick={() => setCategoryFilter(cat)}
                className={`rounded-full px-3 py-1 text-xs font-semibold transition ${
                  categoryFilter === cat
                    ? 'bg-emerald-600 text-white shadow-xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>

          <div className="grid gap-3 sm:grid-cols-2 max-h-[600px] overflow-y-auto pr-1">
            {filteredProducts.map(p => (
              <div key={p.id} className="flex flex-col justify-between rounded-xl border border-slate-200 p-3.5 bg-white transition hover:border-emerald-300 hover:shadow-xs">
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between gap-1">
                    <span className="text-[10px] uppercase font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-100">
                      {p.category}
                    </span>
                    {p.availability && (
                      <span className="text-[10px] text-emerald-600 bg-emerald-50/50 px-1.5 py-0.5 rounded font-medium">
                        {p.availability}
                      </span>
                    )}
                  </div>
                  <div className="text-sm font-semibold text-slate-800 line-clamp-2" title={p.name}>
                    {p.name}
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
                    {p.seller_name && (
                      <span className="inline-flex items-center gap-1 font-medium text-slate-600">
                        <Store className="h-3 w-3 text-slate-400" /> {p.seller_name}
                      </span>
                    )}
                    {p.size_or_dimension && (
                      <span className="bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded text-[11px]">
                        {p.size_or_dimension}
                      </span>
                    )}
                    {p.wet_weight_kg && (
                      <span className="bg-emerald-50 text-emerald-700 border border-emerald-200/60 px-1.5 py-0.5 rounded text-[11px] font-medium">
                        {p.wet_weight_kg} kg wet load
                      </span>
                    )}
                  </div>
                </div>

                <div className="mt-3 flex items-center justify-between pt-2 border-t border-slate-100">
                  <div className="flex flex-col">
                    <span className="text-base font-black text-slate-900">
                      ৳{Number(p.price_bdt || 0).toLocaleString()}
                    </span>
                    <span className="text-[10px] text-slate-400">
                      {p.price_unit || p.unit || 'per unit'}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5">
                    {p.product_url && (
                      <a
                        href={p.product_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 rounded-lg border border-slate-200 bg-slate-50/70 px-2 py-1.5 text-xs text-slate-700 hover:text-emerald-800 hover:border-emerald-300 transition"
                        title="Open direct product link at retailer store"
                      >
                        <ExternalLink className="h-3.5 w-3.5" /> Store
                      </a>
                    )}
                    <button
                      onClick={() => addToCart({
                        product_id: p.id,
                        name: p.name,
                        unit_price_bdt: p.price_bdt,
                        qty: 1
                      })}
                      className="flex items-center gap-1 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 transition shadow-xs"
                    >
                      <Plus className="h-3.5 w-3.5" /> Add
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Cart & Checkout Panel */}
        <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm space-y-6">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <ShoppingBag className="h-5 w-5 text-emerald-600" />
              <h3 className="font-bold text-slate-900">Your Cart ({cart.length})</h3>
            </div>
            {cart.length > 0 && (
              <button onClick={clearCart} className="text-xs text-red-500 hover:underline">
                Clear
              </button>
            )}
          </div>

          {cart.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-400">
              Your cart is empty. Add recommended materials or items from the catalog.
            </div>
          ) : (
            <div className="space-y-3 max-h-60 overflow-y-auto pr-1">
              {cart.map((item, i) => (
                <div key={i} className="flex items-center justify-between rounded-xl bg-slate-50 p-2.5 text-xs">
                  <div className="flex-1 pr-2">
                    <div className="font-semibold text-slate-800 line-clamp-1">{item.name}</div>
                    <div className="text-slate-500">
                      {item.qty} × ৳{(item.unit_price_bdt || item.price_bdt || 0).toLocaleString()}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-900">
                      ৳{(item.qty * (item.unit_price_bdt || item.price_bdt || 0)).toLocaleString()}
                    </span>
                    <button
                      onClick={() => removeFromCart(item.product_id || item.id)}
                      className="text-slate-400 hover:text-red-500"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {cart.length > 0 && (
            <div className="space-y-4 border-t border-slate-100 pt-4">
              <div className="flex justify-between text-sm font-bold text-slate-900">
                <span>Subtotal:</span>
                <span className="text-emerald-700">৳{cartTotal.toLocaleString()}</span>
              </div>

              {/* Payment selector */}
              <div className="space-y-2">
                <span className="text-xs font-semibold text-slate-700 block">Payment Method:</span>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <button
                    type="button"
                    onClick={() => setPaymentMethod('cod')}
                    className={`flex items-center justify-center gap-1.5 rounded-xl border p-2.5 font-medium transition ${
                      paymentMethod === 'cod'
                        ? 'border-emerald-500 bg-emerald-50 text-emerald-800'
                        : 'border-slate-200 text-slate-600'
                    }`}
                  >
                    <Truck className="h-4 w-4" /> Cash on Delivery
                  </button>
                  <button
                    type="button"
                    onClick={() => setPaymentMethod('sandbox')}
                    className={`flex items-center justify-center gap-1.5 rounded-xl border p-2.5 font-medium transition ${
                      paymentMethod === 'sandbox'
                        ? 'border-emerald-500 bg-emerald-50 text-emerald-800'
                        : 'border-slate-200 text-slate-600'
                    }`}
                  >
                    <CreditCard className="h-4 w-4" /> Sandbox (bKash)
                  </button>
                </div>
              </div>

              <button
                onClick={handleCheckout}
                disabled={checkoutLoading}
                className="w-full rounded-xl bg-emerald-600 py-3 text-sm font-semibold text-white shadow-md shadow-emerald-600/25 hover:bg-emerald-700 transition"
              >
                {checkoutLoading ? 'Processing Order...' : `Place Order (৳${cartTotal.toLocaleString()})`}
              </button>
            </div>
          )}

          {/* Last Order Confirmation */}
          {lastOrder && (
            <div className="rounded-xl bg-emerald-50 border border-emerald-200 p-4 space-y-3">
              <div className="flex items-center gap-2 text-xs font-bold text-emerald-800">
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                Order Placed Successfully!
              </div>
              <div className="text-xs text-slate-600 space-y-1">
                <div>Order ID: <span className="font-mono font-bold text-slate-800">{lastOrder.order_id}</span></div>
                <div>Status: <span className="font-semibold uppercase text-emerald-700">{lastOrder.status}</span></div>
                <div>Total: <span className="font-bold">৳{lastOrder.total_bdt?.toLocaleString()}</span></div>
              </div>

              {lastOrder.sandbox_token && lastOrder.status !== 'paid' && (
                <div className="pt-2">
                  <button
                    onClick={handleSimulatePayment}
                    className="w-full rounded-lg bg-emerald-700 py-2 text-xs font-semibold text-white hover:bg-emerald-800"
                  >
                    Simulate Sandbox Payment Webhook
                  </button>
                </div>
              )}

              {webhookStatus && (
                <div className="text-[11px] font-semibold text-emerald-800 bg-white/80 p-2 rounded-lg">
                  {webhookStatus}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Nav Buttons */}
      <div className="flex justify-between items-center pt-2">
        <button
          onClick={onBack}
          className="flex items-center gap-2 rounded-xl border border-slate-200 px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition"
        >
          <ChevronLeft className="h-4 w-4" />
          Back to Growing Guide
        </button>
        <button
          onClick={onNext}
          className="flex items-center gap-2 rounded-xl bg-emerald-600 px-6 py-2.5 text-sm font-semibold text-white shadow-md shadow-emerald-600/25 hover:bg-emerald-700 transition"
        >
          Proceed to AI Plant Doctor
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
