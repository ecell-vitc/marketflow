import { useEffect } from 'react'
import { useAuthStore, useUserStore } from './lib/store'
import { makeRequest } from './lib/utils'
import { NavLink, BrowserRouter, Routes, Route } from 'react-router'

import Stock from './pages/stock/page'
// import Portfolio from './pages/portfolio/page'
import HomePage from './pages/auth/page'
import TransactionPage from './pages/transactions/page'
import Leaderboard from './pages/leaderboard/page'
import AdminPage from './pages/admin/page'


const ProtectedRoute = ({ elem }: { elem: React.ReactNode }) => {
	const logged = useAuthStore(state => state.logged)
	
	return (logged ? elem :
		<div className='text-white mt-[6rem] px-10'>
			You are not logged in. Please <NavLink className="underline" to="/">login</NavLink> to continue.
		</div>
	)
}


const App = () => {
	const login = useAuthStore(state => state.setLogged)
	const profile = useUserStore(state => state.update)

	useEffect(() => {
		const token = localStorage.getItem('token')
		if (token) {
			login(true)
			makeRequest('user', 'GET', undefined, true)
				.then(res => profile(res["balance"], res["owned"]))
			
		}

		// const socket = new WebSocket(`wss://${SERVER_HOST}/news/`)
		// socket.onmessage = (ev: MessageEvent) => showMessage(JSON.parse(ev.data).message)
		// socket.onclose = () => { if (socket.readyState === WebSocket.CLOSED) alert("Connection interrupted! Please refresh!") }
		
		// return () => { if (socket.readyState === WebSocket.OPEN) socket.close() }
	}, [login, profile])

	return (
		<>
			<div id="toast" className="text-white py-3 px-5 fixed transition right-[25px] w-[300px] rounded z-[99999]"></div>

			<BrowserRouter>
				<Navbar />
				<main>
					<Routes>
						<Route path="/stocks" element={<ProtectedRoute elem={<Stock />} />} />
						{/* <Route path="/portfolio" element={<Portfolio />} /> */}
						<Route path="/transactions" element={<ProtectedRoute elem={<TransactionPage />} />} />
						<Route path="/leaderboard" element={<Leaderboard />} />
						<Route path="/admin" element={<AdminPage />} />
						<Route path="/" element={<HomePage />} />
					</Routes>
				</main>
			</BrowserRouter>
		</>
	)
}

const Navbar = () => {
	const logged = useAuthStore(state => state.logged)

	return (
		<nav className='flex justify-between px-10 md:px-24 items-center'>
			<NavLink to="/">
				<img src="/favicon/android-chrome-192x192.png" width={50} height={50} alt="" />
			</NavLink>

			<div className="inline-flex gap-5">
				<NavLink to="/">Home</NavLink>
				{!logged ? <></> :
					<>
						<NavLink to="/stocks">Stocks</NavLink>
						{/* <NavLink to="/portfolio">Portfolio</NavLink> */}
						<NavLink to="/transactions">Transactions</NavLink>
					</>
				}
				<NavLink to="/leaderboard">Leaderboard</NavLink>
				{!logged ? <></> :
					<a href="#" onClick={() => {
						localStorage.removeItem("token")
						window.location.href = "/"
					}}>Logout</a>
				}
			</div>
		</nav>
	)
}

export default App
