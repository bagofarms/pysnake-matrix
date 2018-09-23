# Development notes (real readme to follow)
* A food pellet is placed at a random location (not the snake body or an existing food pellet) every certain number of loops
* The snake is updated
  * Update the head
    * A body segment is added in the direction of movement or in the direction of the keyboard command
    * If the body can't move that direction (like backwards), just move forward as if no command was issued
    * If the new segment occupies the same space as an existing segment, return false, indicating that the snake is dead.  Maybe set a flag on the snake and check it in the main loop?
  * Update the tail
    * If we grew in the last loop (set a flag on the snake?), leave the tail where it is and increment the length.  Or maybe it's increasing the stack size or something
    * If we didn't grow, remove the tail body segment
* If the snake head occupies the same space as food
  * set the grow flag on the snake
  * remove that pellet from the play area
* Update the screen
  * Get canvas
  * Set all pixels to black
  * Get list of food locations and write those pixels
  * Get list of snake body locations and write those pixels
  * Write canvas to screen
* Wait for the prescribed amount of time until the next loop while listening for arrow keys
* If an arrow key is captured during the wait, set the command to that direction.
