
import pygame
from time import sleep
import sys
import random
from math import sqrt
import pickle
from multiprocessing import Process, Pipe

class DrawableObject:
	def __init__(self, screen ,pos = None, color = None, dimensions = None):
		self.pos = pos
		self.color = color
		self.dimensions = dimensions
		self.screen = screen

	def draw(self):
		global unitWidth, unitHeight
		pygame.draw.rect(
			self.screen, self.color,
			pygame.Rect(
				self.pos[0] * unitWidth,
				self.pos[1] * unitHeight,
				self.dimensions[0] * unitWidth,
				self.dimensions[1] * unitHeight)
		)

	def setAndDraw(self,
		pos = None, color = None, dimensions = None):
		global unitWidth, unitHeight
		if pos: self.pos = pos
		if color: self.color = color
		if dimensions: self.dimensions = dimensions
		self.draw()

	def notSetAndDraw(self,
		pos = None, color = None, dimensions = None):
		global unitWidth, unitHeight
		pygame.draw.rect(
			self.screen, color if color else self.color,
			pygame.Rect(
				(pos[0] if pos else self.pos[0]) * unitWidth,
				(pos[1] if pos else self.pos[1]) * unitHeight,
				(dimensions[0] if dimensions else self.dimensions[0]) * unitWidth,
				(dimensions[1] if dimensions else self.dimensions[1]) * unitHeight)
		)

def randomPaddleMovement(leftPaddle):
	global cellsHeight
	if leftPaddle.pos[1] == 1:
		paddleModY = random.choice([0, 1])
	elif leftPaddle.pos[1] == cellsHeight - 4:
		paddleModY = random.choice([0, -1])
	else:
		paddleModY = random.choice([0, -1, 1])
	leftPaddle.pos = (leftPaddle.pos[0], leftPaddle.pos[1] + paddleModY)

def getNewBallPos_and_Mod(returnBallPos, posMod, leftPaddlePos, rightPaddlePos):
	global cellsHeight, cellsWidth

	# Generate new position.
	newBallPos = (returnBallPos[0] + posMod[0], returnBallPos[1] + posMod[1])
	# The ball hits upperBorder AND leftPaddle.
	if newBallPos == (0, 0) and leftPaddlePos[1] == 1:
		posMod = (1, 1)
		returnBallPos = (2, 2)
	# The ball hits lowerBorder AND leftPaddle.
	elif newBallPos == (0, cellsHeight - 1)\
		and leftPaddlePos[1] == cellsHeight - 4:
		posMod = (1, -1)
		returnBallPos = (2, cellsHeight - 3)
	# The ball hits lowerBorder AND rightPaddle.
	elif newBallPos == (cellsWidth - 1, cellsHeight - 1)\
		and rightPaddlePos[1] == cellsHeight - 4:
		posMod = (-1, -1)
		returnBallPos = (cellsWidth - 3, cellsHeight - 3)
	# The ball hits upperBorder AND rightPaddle.
	elif newBallPos == (cellsWidth - 1, 0)\
		and rightPaddlePos[1] == 1:
		posMod = (-1, 1)
		returnBallPos = (cellsWidth - 3, 2)
	# The ball touches ONLY the left paddle.
	elif newBallPos[0] == 0\
		and leftPaddlePos[1] <= newBallPos[1] and newBallPos[1] < leftPaddlePos[1] + 3:
		if posMod == (-1, -1):
			posMod = (1, -1)
		elif posMod == (-1, 0):
			posMod = (1, 0)
		else:
			posMod = (1, 1)
		returnBallPos = (returnBallPos[0] + posMod[0], returnBallPos[1] + posMod[1])
	# The ball touches ONLY the right paddle.
	elif newBallPos[0] == cellsWidth - 1\
		and rightPaddlePos[1] <= newBallPos[1] and newBallPos[1] < rightPaddlePos[1] + 3:
		if posMod == (1, 1):
			posMod == (-1, 1)
		elif posMod == (1, 0):
			posMod = (-1, 0)
		else:
			posMod = (-1, -1)
		returnBallPos = (returnBallPos[0] + posMod[0], returnBallPos[1] + posMod[1])
	# The ball touches ONLY the upper border.
	elif newBallPos[1] == 0:
		if posMod == (1, -1):
			posMod = (1, 1)
		else:
			posMod = (-1, 1)
		returnBallPos = (returnBallPos[0] + posMod[0], returnBallPos[1] + posMod[1])
	# The ball touches ONLY the lower border.
	elif newBallPos[1] == cellsHeight - 1:
		if posMod == (-1, 1):
			posMod = (-1, -1)
		else:
			posMod = (1, -1)
		returnBallPos = (returnBallPos[0] + posMod[0], returnBallPos[1] + posMod[1])
	# The ball continues its journey.
	else:
		returnBallPos = (returnBallPos[0] + posMod[0], returnBallPos[1] + posMod[1])

	return (returnBallPos, posMod)

def getAvailableActions(paddleY):
	global cellsHeight
	availableActions = [0]
	if paddleY > 2: availableActions.append(-1)
	if paddleY < cellsHeight - 5: availableActions.append(1)
	return availableActions

def epsQ_learningPaddleMovement(paddle, Q, ball, posMod, previousActions,\
	epsilon=0.8):
	global cellsHeight

	availableActions = getAvailableActions(paddle.pos[1])

	unexploredAct = list(filter(\
		lambda a: (paddle.pos, ball.pos, posMod, a) not in Q, availableActions))

	if unexploredAct:
		paddleModY = random.choice(unexploredAct)
		paddle.pos = (paddle.pos[0], paddle.pos[1] + paddleModY)
		previousActions.append((paddle.pos, ball.pos, posMod, paddleModY,))
	else:
		if random.random() < epsilon:
			paddleModY = random.choice(availableActions)
			paddle.pos = (paddle.pos[0], paddle.pos[1] + paddleModY)
			previousActions.append((paddle.pos, ball.pos, posMod, paddleModY,))
		else:
			Q_learningPaddleMovement(paddle, Q, ball, posMod, previousActions)

def Q_learningPaddleMovement(paddle, Q, ball, posMod, previousActions, f=lambda x: x):
	global cellsHeight

	availableActions = getAvailableActions(paddle.pos[1])

	bestChoice = availableActions[0]
	if f((paddle.pos, ball.pos, posMod, bestChoice)) in Q:
		bestScore = Q[f((paddle.pos, ball.pos, posMod, bestChoice))]
	else:
		# val = 2 * random.random() - 1
		val = 0
		Q[f((paddle.pos, ball.pos, posMod, bestChoice))] = val
		bestScore = val


	for a in availableActions[1:]:
		if f((paddle.pos, ball.pos, posMod, a)) not in Q:
			# val = 2 * random.random() - 1
			val = 0
			Q[f((paddle.pos, ball.pos, posMod, a))] = val
		if Q[f((paddle.pos, ball.pos, posMod, a))] >= bestScore:
			bestScore = Q[f((paddle.pos, ball.pos, posMod, a))]
			bestChoice = a

		paddle.pos = (paddle.pos[0], paddle.pos[1] + bestChoice)
		previousActions.append(f((paddle.pos, ball.pos, posMod, bestChoice,)))

def almotPerfPlayer(paddle, ball, prob):
	availableActions = getAvailableActions(paddle.pos[1])

	samp = random.random()
	if samp < prob:
		newBestAct = availableActions[0]
		bestDist = abs(paddle.pos[1] + newBestAct - ball.pos[1])

		for a in availableActions:
			dist = abs(paddle.pos[1] + a - ball.pos[1])
			if dist < bestDist:
				bestDist = dist
				newBestAct = a
	else:
		newBestAct = random.choice(availableActions)

	paddle.pos = (paddle.pos[0], paddle.pos[1] + newBestAct)

def updateQ(Q, previousStates, reward,  orientation\
	,alpha=0.7, gama=0.8, isLeftFlag=True):
	global cellsWidth, cellsHeight, rightPaddle, leftPaddle

	if reward >= 0:
		touchedThePaddle = False
		for prevSt in previousStates:
			if abs(prevSt[0][0] - prevSt[1][0]) == 1\
				and prevSt[0][1] <= prevSt[1][1] < prevSt[0][1] + 3:
				touchedThePaddle = True
				break
		if not touchedThePaddle:
			return

	if not previousStates:
		return

	if previousStates[-1] not in Q:
		# val = 2 * random.random() - 1
		val = 0
		Q[previousStates[-1]] = val

	Q[previousStates[-1]] = Q[previousStates[-1]] = (1 - alpha) * Q[previousStates[-1]] + alpha *\
		reward

	for i in range(len(previousStates)-1):
		currentPaddlePos, currentBallPos, currentPosMod = previousStates[i][:-1]
		# Next ball position and ball movement direction are calculated.
		if isLeftFlag:
			nextBallPos, nextPosMod = getNewBallPos_and_Mod(currentBallPos, currentPosMod,\
				currentPaddlePos, rightPaddle.pos)
		else:
			nextBallPos, nextPosMod = getNewBallPos_and_Mod(currentBallPos, currentPosMod,\
				leftPaddle.pos, currentPaddlePos)
		# The next state is determined.
		nextPaddlePos = (currentPaddlePos[0], currentPaddlePos[1] + previousStates[i][-1])
		nextState = (nextPaddlePos, nextBallPos, nextPosMod)

		availableActions = getAvailableActions(nextPaddlePos[1])

		maxQ = -500000
		for a in availableActions:
			if nextState + (a,) in Q\
				and Q[nextState + (a,)] > maxQ:
				maxQ = Q[nextState + (a,)]

		if maxQ == -500000:
			maxQ = 0

		dist = previousStates[i][1][0] - previousStates[i][0][0]
		if previousStates[i][-2] in orientation:
			scaledReward = reward * ((2*(cellsWidth - 3)) - dist) / (2*(cellsWidth - 3))
		else:
			scaledReward = reward * dist / (2*(cellsWidth - 3))

		Q[previousStates[i]] = (1 - alpha) *\
			(Q[previousStates[i]] if previousStates[i] in Q else 0)+\
			alpha * ( scaledReward + gama * maxQ )

def updateParams(diff):
	global leftScore, rightScore, alpha, gama, previousDiff, epsilon

	alphaTerm = -0.0005
	gamaTerm = 0.001
	epsilonTerm = -0.001

	if diff > previousDiff:
		if 0 <= alpha + alphaTerm < 1:
			alpha += alphaTerm
		if 0 <= gama + gamaTerm < 1:
			gama += gamaTerm
		if 0 <= epsilon + epsilonTerm < 1:
			epsilon += epsilonTerm
	else:
		if 0 <= alpha - alphaTerm < 1:
			alpha -= alphaTerm
		if 0 <= gama - gamaTerm < 1:
			gama -= gamaTerm
		if 0 <= epsilon - epsilonTerm < 1:
			epsilon -= epsilonTerm
	previousDiff = diff

def reverseKey_rightToLeft(key):
	return ((0, key[0][1]), key[1],\
		(key[2][0]*(-1), key[2][1]), key[-1])

def reverseKey_leftToRight(key):
	global cellsWidth
	return ((cellsWidth-1, key[0][1]), key[1],\
		(key[2][0]*(-1), key[2][1]), key[-1])

def reverseQ_leftToRight(Q):
	newQ = {}
	for key, value in Q.items():
		newQ[reverseKey_leftToRight(key)] = value
	return newQ

def statShow(conn):
	pygame.init()
	pygame.font.init()
	myfont = pygame.font.SysFont('Comic Sans MS', 30)
	screen = pygame.display.set_mode((200, 300), pygame.HWSURFACE
		| pygame.DOUBLEBUF
		| pygame.RESIZABLE)
	while True:
		paramsDict = conn.recv()
		if not paramsDict:
			break
		screen.fill((255, 255, 255))

		y = 0
		for p in paramsDict:
			text = p[0] + " => " + str('%.2f' % p[1])
			textsurface = myfont.render(text, False, (0, 0, 0))
			screen.blit(textsurface,(0,y))
			y+=40
		pygame.display.flip()

if __name__ == "__main__":

	global cellsHeight, diag, cellsWidth
	cellsWidth = int(sys.argv[1])
	cellsHeight = int(sys.argv[2])
	if len(sys.argv) == 4:
		numberOfMatches = int(sys.argv[3])
	else:
		numberOfMatches = 500

	parent_conn, child_conn = Pipe()
	statProc = Process(target=statShow, args=(child_conn,))
	statProc.start()

	global unitWidth, unitHeight, leftPaddle, rightPaddle
	pygame.init()
	screen = pygame.display.set_mode((400, 300), pygame.HWSURFACE
		| pygame.DOUBLEBUF
		| pygame.RESIZABLE)

	ball = DrawableObject(
		screen,
		(cellsWidth/2, cellsHeight/2,),
		(255, 0, 0,),
		(1, 1,)
	)

	leftPaddle = DrawableObject(
		screen,
		(0, cellsHeight/2,),
		(0, 255, 0,),
		(1, 3,)
	)

	rightPaddle = DrawableObject(
		screen,
		(cellsWidth-1, cellsHeight/2 - 1,),
		(0, 255, 0,),
		(1, 3,)
	)

	upperBorder = DrawableObject(
		screen,
		(0, 0,),
		(0, 128, 255),
		(cellsWidth, 1,)
	)

	lowerBorder = DrawableObject(
		screen,
		(0, cellsHeight - 1,),
		(0, 128, 255),
		(cellsWidth, 1,)
	)

	posModifiers = [(-1, -1), (-1, 0), (-1, 1), (1, 1), (1, 0), (1, -1)]

	posMod = random.choice(posModifiers)

	global leftScore, rightScore, alpha, gama, previousDiff, epsilon
	leftScore = 0
	rightScore = 0
	previousDiff = 0

	trainingFlag = True

	if trainingFlag:
		leftQ = {}
	else:
		leftQ = pickle.load( open( "save.p", "rb" ) )
		# rightQ  = reverseQ_leftToRight(pickle.load( open( "save.p", "rb" ) ))

	leftPreviousStates = []

	alpha = 0.9
	gama = 0.2
	epsilon = 0.4

	plotData = [[], []]
	stepDuration = 5
	done = False
	numOfMoves = 0

	while not done:
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				done = True
			elif event.type==pygame.VIDEORESIZE:
				pygame.display.set_mode(event.dict['size'],
					pygame.HWSURFACE
					| pygame.DOUBLEBUF
					| pygame.RESIZABLE)

		screen.fill((0,0,0))

		infoObject = pygame.display.Info()

		unitWidth = int(float(infoObject.current_w)/cellsWidth)
		unitHeight = int(float(infoObject.current_h)/cellsHeight)

		# Draw upper limit.
		upperBorder.draw()

		# Draw lower limit.
		lowerBorder.draw()

		# Draw left paddle.
		leftPaddle.draw()

		# Draw right paddle.
		rightPaddle.draw()

		# Draw ball.
		ball.draw()

		if numOfMoves > 3 * (cellsHeight + cellsWidth):
			ball.pos = (cellsWidth/2, cellsHeight/2,)
			posMod = random.choice(posModifiers)

			numOfMoves = 0
		# Right agent scores a point.
		elif ball.pos[0] == 0:

			dist =  (ball.pos[1] - leftPaddle.pos[1] - 2) if ball.pos[1] > leftPaddle.pos[1] else\
				leftPaddle.pos[1] - ball.pos[1]

			if trainingFlag:
				updateQ(leftQ, leftPreviousStates, -1 * dist / (cellsHeight-6), [(-1, -1), (-1, 0), (-1, 1)], alpha, gama)

			rightScore += 1
			ball.pos = (cellsWidth/2, cellsHeight/2,)
			posMod = random.choice(posModifiers)

			updateParams(leftScore - rightScore)

			plotData[0].append(leftScore + rightScore)
			plotData[1].append(leftScore - rightScore)

			numOfMoves = 0
			leftPreviousStates = []
		# Left agent scores a point.
		elif ball.pos[0] == cellsWidth - 1:

			if trainingFlag:
				updateQ(leftQ, leftPreviousStates, 1, [(-1, -1), (-1, 0), (-1, 1)], alpha, gama)

			leftScore += 1
			ball.pos = (cellsWidth/2, cellsHeight/2,)
			posMod = random.choice(posModifiers)

			updateParams(leftScore - rightScore)

			plotData[0].append(leftScore + rightScore)
			plotData[1].append(leftScore - rightScore)

			numOfMoves = 0
			leftPreviousStates = []
		else:
			ball.pos, posMod = getNewBallPos_and_Mod(ball.pos, posMod, leftPaddle.pos, rightPaddle.pos)

			# Moving the left paddle.
			Q_learningPaddleMovement(leftPaddle, leftQ, ball,\
				posMod, leftPreviousStates)
			# epsQ_learningPaddleMovement(leftPaddle, leftQ, ball,\
			# 	posMod, leftPreviousStates, epsilon)
			# randomPaddleMovement(leftPaddle)

			# Moving the right paddle.
			randomPaddleMovement(rightPaddle)
			# Q_learningPaddleMovement(rightPaddle, leftQ,\
			# 	ball, posMod, [], reverseKey_rightToLeft)
			# epsQ_learningPaddleMovement(rightPaddle, rightQ, ball,\
			# 	posMod, [], epsilon)
			# almotPerfPlayer(rightPaddle, ball, alpha)

		numOfMoves += 1
		if leftScore + rightScore == numberOfMatches:
			done = True

		pygame.display.flip()

		parent_conn.send([\
			("left score", leftScore),\
			("right score", rightScore),\
			("alpha", alpha),\
			("gamma", gama),\
			("epsilon", epsilon)\
		])

		pygame.time.delay(stepDuration)

	from matplotlib import pyplot as plt
	plt.xlabel("Episode")
	plt.ylabel("Difference")
	plt.plot(
		plotData[0],
		plotData[1],
		linewidth = 1.0, color = "blue"
	)
	plt.show()

	# with open('q.txt', 'w') as the_file:
	# 	for key, value in leftQ.items():
	# 		the_file.write(str(key) + " => " + str(value) + "\n")

	if trainingFlag:
		pickle.dump( leftQ, open( "save.p", "wb" ) )

	parent_conn.send(None)
	statProc.join()

	print("leftScore=" + str(leftScore) + "  rightScore=" + str(rightScore))
